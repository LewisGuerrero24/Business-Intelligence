from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from etl_service.core.config import Settings, get_settings
from etl_service.core.progress import NullProcessReporter, ProcessReporter
from etl_service.domain.enums import ErrorType, ImportStatus, Severity
from etl_service.domain.models import ValidationError
from etl_service.domain.process import LoadStats, ValidationStats
from etl_service.etl.loaders.file_loader import read_tabular_file
from etl_service.etl.pipeline import ImportPipeline
from etl_service.etl.registry import get_import_spec
from etl_service.etl.transformers.common import transform_raw_row
from etl_service.etl.validators.common import validate_clean_row
from etl_service.repositories.control_repository import ControlRepository
from etl_service.repositories.dw_repository import DwRepository
from etl_service.repositories.staging_repository import StagingRepository


class ImportService:
    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        reporter: ProcessReporter | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.reporter = reporter or NullProcessReporter()
        self.control = ControlRepository(session, self.settings)
        self.staging = StagingRepository(session, self.settings)
        self.dw = DwRepository(session, self.settings)

    def create_import_from_file(
        self,
        *,
        company_id: str,
        import_type: str,
        file_path: str | Path,
        source_type: str,
        created_by: str | None = None,
        process_now: bool = False,
    ) -> dict[str, Any]:
        spec = get_import_spec(import_type)
        self.reporter.step(
            "Preparando importacion desde archivo",
            import_type=spec.import_type,
            source_type=source_type,
            file_path=str(file_path),
        )
        if not self.dw.company_exists(company_id):
            raise ValueError(
                f"company_id {company_id} does not exist in "
                f"{self.settings.dw_schema}.companies."
            )

        path = Path(file_path)
        self.reporter.step("Leyendo archivo de origen", file_path=str(path))
        rows = read_tabular_file(path, chunk_size=self.settings.default_batch_size)
        file_size = path.stat().st_size if path.exists() else None
        self.reporter.success("Archivo leido", total_records=len(rows))

        self.reporter.step("Registrando importacion y cargando staging")
        import_id = self.control.create_import(
            company_id=company_id,
            import_type=spec.import_type,
            source_type=source_type,
            original_filename=path.name,
            file_path=str(path),
            file_size_bytes=file_size,
            total_records=len(rows),
            created_by=created_by,
        )
        inserted = self.staging.bulk_insert_rows(
            import_id=str(import_id),
            spec=spec,
            rows=rows,
        )
        self.control.update_status(
            import_id=import_id,
            status=ImportStatus.UPLOADED,
            total_records=len(rows),
            processed_records=inserted,
        )
        self.session.commit()
        self.reporter.success(
            "Staging cargado",
            import_id=str(import_id),
            staging_records=inserted,
        )

        if process_now:
            return self.process_import(import_id)

        return {
            "import_id": str(import_id),
            "status": ImportStatus.UPLOADED.value,
            "total_records": len(rows),
            "staging_records": inserted,
        }

    def process_import(self, import_id: str | UUID) -> dict[str, Any]:
        pipeline = ImportPipeline(self.session, self.settings, reporter=self.reporter)
        return pipeline.process_import(import_id)

    def _validate_pending_rows(
        self,
        *,
        import_id: str,
        spec,
        company_id: str | None,
    ) -> ValidationStats:
        stats = ValidationStats()
        self.reporter.step("Transformando y validando filas pendientes")

        while True:
            rows = self.staging.fetch_rows_for_validation(
                import_id=import_id,
                spec=spec,
                limit=self.settings.default_batch_size,
            )
            if not rows:
                break

            for row in rows:
                clean_data = transform_raw_row(row["raw_data"] or {}, spec, company_id)
                errors = validate_clean_row(clean_data, spec, row["row_number"])
                stats.add_result(errors)
                self.staging.save_validation_result(
                    spec=spec,
                    staging_id=str(row["staging_id"]),
                    clean_data=clean_data,
                    errors=errors,
                )
                self.control.insert_errors(import_id, errors)

            self.session.commit()
            self.reporter.success(
                "Lote de validacion procesado",
                read_records=stats.read_records,
                valid_records=stats.valid_records,
                invalid_records=stats.invalid_records,
            )

        return stats

    def _load_valid_rows(self, *, import_id: str, spec) -> LoadStats:
        stats = LoadStats()
        self.reporter.step("Cargando filas validas al Data Warehouse")

        while True:
            rows = self.staging.fetch_valid_rows_for_load(
                import_id=import_id,
                spec=spec,
                limit=self.settings.default_batch_size,
            )
            if not rows:
                break

            for row in rows:
                try:
                    _, action = self.dw.upsert_clean_row(
                        spec=spec,
                        clean_data=row["clean_data"] or {},
                    )
                    self.staging.mark_loaded(spec=spec, staging_id=str(row["staging_id"]))
                    self.session.commit()
                    stats.add_success(action)
                except SQLAlchemyError as exc:
                    self.session.rollback()
                    stats.add_failure()
                    errors = [self._build_load_error(row_number=row["row_number"], exc=exc)]
                    self.control.insert_errors(import_id, errors)
                    self.staging.mark_failed(
                        spec=spec,
                        staging_id=str(row["staging_id"]),
                        errors=errors,
                    )
                    self.session.commit()

            self.reporter.success(
                "Lote de carga procesado",
                read_records=stats.read_records,
                inserted_records=stats.inserted_records,
                updated_records=stats.updated_records,
                failed_records=stats.failed_records,
            )

        return stats

    def _build_load_error(self, *, row_number: int, exc: SQLAlchemyError) -> ValidationError:
        message = str(exc.orig if getattr(exc, "orig", None) else exc)
        lowered = message.lower()

        if "foreign key" in lowered or "violates foreign key" in lowered:
            error_type = ErrorType.FK_VIOLATION
            suggested_fix = (
                "Verify that the referenced company, branch, product, customer, "
                "or supplier exists."
            )
        elif "invalid input syntax" in lowered or "cannot cast" in lowered:
            error_type = ErrorType.DATA_TYPE
            suggested_fix = "Verify field formats before importing this row again."
        elif "duplicate key" in lowered or "unique constraint" in lowered:
            error_type = ErrorType.DUPLICATE
            suggested_fix = "Verify whether the row already exists in the DW table."
        else:
            error_type = ErrorType.BUSINESS_RULE
            suggested_fix = "Review the row data and database constraints."

        return ValidationError(
            row_number=row_number,
            error_type=error_type.value,
            severity=Severity.ERROR.value,
            field_name=None,
            field_value=None,
            expected_format=None,
            error_message=message[:1000],
            suggested_fix=suggested_fix,
        )

    def _determine_final_status(self, counts: dict[str, int]) -> ImportStatus:
        if counts["total_records"] == 0:
            return ImportStatus.FAILED
        if counts["success_records"] > 0 and counts["failed_records"] > 0:
            return ImportStatus.PARTIAL
        if counts["success_records"] > 0 and counts["failed_records"] == 0:
            return ImportStatus.COMPLETED
        return ImportStatus.FAILED

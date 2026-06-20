import json
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from etl_service.core.config import Settings, get_settings
from etl_service.core.progress import NullProcessReporter, ProcessReporter
from etl_service.etl.pipeline import ImportPipeline
from etl_service.etl.preclean.header_normalizer import compact_field_name
from etl_service.etl.registry import get_import_spec
from etl_service.repositories.control_repository import ControlRepository
from etl_service.repositories.dw_repository import DwRepository
from etl_service.repositories.staging_repository import StagingRepository


class CorrectionService:
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

    def get_correction_by_error(
        self,
        *,
        error_id: str | UUID,
        company_id: str | UUID | None = None,
    ) -> dict[str, Any]:
        context = self._error_context(error_id=error_id, company_id=company_id)
        row = self._failed_staging_row_from_context(context)
        errors = self.control.get_errors_by_rows(
            context["import_id"],
            [int(context["row_number"])],
        ).get(int(context["row_number"]), [])
        item = self._correction_item(
            row=row,
            errors=errors,
            editable_columns=self._editable_columns(context["spec"]),
        )
        resolved_company_id = str(context["import_info"]["company_id"])
        return {
            "error_id": str(error_id),
            "import_id": context["import_id"],
            "company_id": resolved_company_id,
            "import_type": context["spec"].import_type,
            **item,
        }

    def apply_correction_by_error(
        self,
        *,
        error_id: str | UUID,
        company_id: str | UUID,
        correction_data: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(correction_data, dict) or not correction_data:
            raise ValueError("correction_data must be a non-empty object.")

        context = self._error_context(error_id=error_id, company_id=company_id)
        spec = context["spec"]
        import_id = context["import_id"]
        row_number = int(context["row_number"])
        staging_row = self._failed_staging_row_from_context(context)
        staging_id = str(staging_row["staging_id"])

        merged_data = self._merge_correction_data(
            spec=spec,
            staging_row=staging_row,
            correction_data=correction_data,
        )
        self.control.delete_errors_for_rows(import_id, [row_number])
        self.staging.apply_correction(
            spec=spec,
            staging_id=staging_id,
            corrected_data=self._filtered_correction_data(spec, merged_data),
        )
        self.staging.reopen_rows(spec=spec, staging_ids=[staging_id])
        self.session.commit()

        pipeline = ImportPipeline(self.session, self.settings, reporter=self.reporter)
        result = pipeline.process_rows(import_id=import_id, staging_ids=[staging_id])

        updated_row = self.staging.get_row_by_row_number(
            import_id=import_id,
            spec=spec,
            row_number=row_number,
        )
        if updated_row is None:
            raise ValueError(f"Staging row not found after correction: {row_number}")

        errors = self.control.get_errors_by_rows(import_id, [row_number]).get(row_number, [])
        clean_data = self._coerce_json(updated_row.get("clean_data"))
        base_message = {
            "error_id": str(error_id),
            "import_id": import_id,
            "import_type": spec.import_type,
            "row_number": row_number,
            "status": "ROW_PROCESSED",
            "clean_data": clean_data,
            "dw_action": {
                "inserted_records": result.get("inserted_records", 0),
                "updated_records": result.get("updated_records", 0),
            },
            "import_status": result.get("status"),
        }

        if errors or not updated_row.get("is_valid"):
            return {
                "success": False,
                "message": None,
                "error": {
                    "error_id": str(error_id),
                    "import_id": import_id,
                    "import_type": spec.import_type,
                    "row_number": row_number,
                    "errors": errors,
                },
            }

        self._learn_successful_correction(
            company_id=str(company_id),
            import_type=spec.import_type,
            original_raw_data=self._coerce_json(staging_row.get("raw_data")),
            correction_data=correction_data,
            allowed_fields=set(spec.columns),
        )
        self.session.commit()

        return {
            "success": True,
            "message": base_message,
            "error": None,
        }

    def _validated_import(self, *, import_id: str | UUID, company_id: str | UUID) -> dict[str, Any]:
        import_info = self.control.get_import(import_id)
        import_company_id = str(import_info.get("company_id"))
        if import_company_id != str(company_id):
            raise ValueError("company_id does not match the import company_id.")
        return import_info

    def _error_context(
        self,
        *,
        error_id: str | UUID,
        company_id: str | UUID | None,
    ) -> dict[str, Any]:
        error = self.control.get_error_by_id(error_id)
        import_id = str(error["import_id"])
        import_info = self.control.get_import(import_id)
        if company_id is not None and str(import_info.get("company_id")) != str(company_id):
            raise ValueError("company_id does not match the import company_id.")
        spec = get_import_spec(str(import_info["import_type"]))
        return {
            "error": error,
            "import_info": import_info,
            "import_id": import_id,
            "row_number": int(error["row_number"]),
            "spec": spec,
        }

    def _failed_staging_row_from_context(self, context: dict[str, Any]) -> dict[str, Any]:
        row = self.staging.get_row_by_row_number(
            import_id=context["import_id"],
            spec=context["spec"],
            row_number=int(context["row_number"]),
        )
        if row is None:
            raise ValueError(
                f"Staging row not found for row_number {context['row_number']}."
            )
        if not row.get("is_processed") or row.get("is_valid"):
            raise ValueError(
                f"Row {context['row_number']} is not a failed processed row."
            )
        return row

    def _correction_item(
        self,
        *,
        row: dict[str, Any],
        errors: list[dict[str, Any]],
        editable_columns: tuple[str, ...],
    ) -> dict[str, Any]:
        raw_data = self._coerce_json(row.get("raw_data"))
        clean_data = self._coerce_json(row.get("clean_data"))
        correction_data = {
            column: clean_data.get(column, raw_data.get(column))
            for column in editable_columns
        }
        fields_to_fix = sorted(
            {
                error["field_name"]
                for error in errors
                if error.get("field_name")
            }
        )
        return {
            "row_number": row["row_number"],
            "staging_id": str(row["staging_id"]),
            "error_ids": [
                str(error["error_id"])
                for error in errors
                if error.get("error_id")
            ],
            "fields_to_fix": fields_to_fix,
            "errors": errors,
            "raw_data": raw_data,
            "clean_data": clean_data,
            "correction_data": correction_data,
        }

    def _editable_columns(self, spec) -> tuple[str, ...]:
        excluded = {spec.dw_pk, "company_id", "company_id_fk", "created_at", "created_by"}
        return tuple(column for column in spec.columns if column not in excluded)

    def _filtered_correction_data(self, spec, correction_data: dict[str, Any]) -> dict[str, Any]:
        allowed_columns = set(spec.columns) - {spec.dw_pk}
        return {
            column: value
            for column, value in correction_data.items()
            if column in allowed_columns
        }

    def _merge_correction_data(
        self,
        *,
        spec,
        staging_row: dict[str, Any],
        correction_data: dict[str, Any],
    ) -> dict[str, Any]:
        clean_data = self._coerce_json(staging_row.get("clean_data"))
        merged = {
            column: value
            for column, value in clean_data.items()
            if column in spec.columns and column != spec.dw_pk
        }
        merged.update(self._filtered_correction_data(spec, correction_data))
        return merged

    def _coerce_json(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

    def _learn_successful_correction(
        self,
        *,
        company_id: str,
        import_type: str,
        original_raw_data: dict[str, Any],
        correction_data: dict[str, Any],
        allowed_fields: set[str],
    ) -> None:
        corrected_values = {
            field: value
            for field, value in correction_data.items()
            if field in allowed_fields and value not in (None, "")
        }
        if not corrected_values:
            return

        for source_field, source_value in original_raw_data.items():
            if source_value in (None, ""):
                continue
            normalized_source = compact_field_name(source_field)
            if normalized_source in allowed_fields:
                continue

            for target_field, target_value in corrected_values.items():
                if str(source_value).strip().lower() != str(target_value).strip().lower():
                    continue
                self.control.learn_field_mapping(
                    company_id=company_id,
                    import_type=import_type,
                    source_field=str(source_field),
                    normalized_source_field=normalized_source,
                    target_field=target_field,
                    confidence=1.0,
                    source="manual_correction",
                )
                break

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from etl_service.core.config import Settings, get_settings
from etl_service.core.progress import NullProcessReporter, ProcessReporter
from etl_service.domain.enums import ImportStatus
from etl_service.domain.process import LoadStats
from etl_service.etl.processors import (
    BranchProcessor,
    CategoryProcessor,
    CustomerProcessor,
    InventoryMovementProcessor,
    ProductProcessor,
    PurchaseDetailProcessor,
    PurchaseProcessor,
    SaleDetailProcessor,
    SaleProcessor,
    SupplierProcessor,
)
from etl_service.etl.processors.base import BaseProcessor
from etl_service.etl.registry import get_import_spec
from etl_service.repositories.control_repository import ControlRepository
from etl_service.repositories.dw_repository import DwRepository
from etl_service.repositories.staging_repository import StagingRepository


PROCESSOR_ORDER: tuple[str, ...] = (
    "branches",
    "categories",
    "suppliers",
    "customers",
    "products",
    "purchases",
    "purchase_details",
    "sales",
    "sales_details",
    "inventory_movement",
)

PROCESSOR_CLASSES: dict[str, type[BaseProcessor]] = {
    "branches": BranchProcessor,
    "categories": CategoryProcessor,
    "suppliers": SupplierProcessor,
    "customers": CustomerProcessor,
    "products": ProductProcessor,
    "purchases": PurchaseProcessor,
    "purchase_details": PurchaseDetailProcessor,
    "purchases_details": PurchaseDetailProcessor,
    "sales": SaleProcessor,
    "sales_details": SaleDetailProcessor,
    "inventory_movement": InventoryMovementProcessor,
}


class ImportPipeline:
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

    def process_import(self, import_id: str | UUID) -> dict[str, Any]:
        self.reporter.step("Consultando importacion", import_id=str(import_id))
        import_info = self.control.get_import(import_id)
        import_type = str(import_info["import_type"]).strip().lower()
        company_id = str(import_info["company_id"]) if import_info.get("company_id") else None
        processor_types = self._processor_types(import_type)

        self.reporter.step(
            "Iniciando pipeline",
            import_id=str(import_id),
            import_type=import_type,
            company_id=company_id,
        )
        self.control.update_status(import_id=import_id, status=ImportStatus.PROCESSING)
        self.session.commit()

        try:
            load_stats = LoadStats()
            counts_by_type: dict[str, dict[str, int]] = {}

            for processor_type in processor_types:
                spec = get_import_spec(processor_type)
                processor = self._build_processor(
                    processor_type=processor_type,
                    company_id=company_id,
                )
                self.reporter.step("Procesando entidad", import_type=processor_type)
                entity_stats = processor.process(import_id=str(import_id))
                load_stats.read_records += entity_stats.read_records
                load_stats.inserted_records += entity_stats.inserted_records
                load_stats.updated_records += entity_stats.updated_records
                load_stats.failed_records += entity_stats.failed_records
                counts_by_type[processor_type] = self.staging.count_states(
                    import_id=str(import_id),
                    spec=spec,
                )
                self.reporter.success(
                    "Entidad procesada",
                    import_type=processor_type,
                    read_records=entity_stats.read_records,
                    inserted_records=entity_stats.inserted_records,
                    updated_records=entity_stats.updated_records,
                    failed_records=entity_stats.failed_records,
                )

            counts = self._combine_counts(counts_by_type)
            final_status = self._final_status(counts)
            self.control.update_status(
                import_id=import_id,
                status=final_status,
                total_records=counts["total_records"],
                processed_records=counts["processed_records"],
                success_records=counts["success_records"],
                failed_records=counts["failed_records"],
                skipped_records=0,
            )
            self.session.commit()

            result = {
                "import_id": str(import_id),
                "status": final_status.value,
                **counts,
                "inserted_records": load_stats.inserted_records,
                "updated_records": load_stats.updated_records,
                "load_failed_records": load_stats.failed_records,
            }
            if counts["failed_records"] > 0:
                result["error_summary"] = self.control.get_error_summary(import_id)
            self.reporter.success(
                "Pipeline finalizado",
                status=final_status.value,
                total_records=counts["total_records"],
                processed_records=counts["processed_records"],
                success_records=counts["success_records"],
                failed_records=counts["failed_records"],
            )
            return result
        except Exception as exc:
            self.session.rollback()
            self.control.update_status(
                import_id=import_id,
                status=ImportStatus.FAILED,
                error_summary=str(exc)[:1000],
            )
            self.session.commit()
            self.reporter.error("Pipeline fallido", import_id=str(import_id), error=str(exc)[:500])
            raise

    def process_rows(self, *, import_id: str | UUID, staging_ids: list[str]) -> dict[str, Any]:
        import_info = self.control.get_import(import_id)
        import_type = str(import_info["import_type"]).strip().lower()
        company_id = str(import_info["company_id"]) if import_info.get("company_id") else None
        spec = get_import_spec(import_type)
        processor = self._build_processor(processor_type=import_type, company_id=company_id)

        self.control.update_status(import_id=import_id, status=ImportStatus.PROCESSING)
        self.session.commit()

        try:
            load_stats = processor.process_rows(
                import_id=str(import_id),
                staging_ids=staging_ids,
            )
            counts = self.staging.count_states(import_id=str(import_id), spec=spec)
            final_status = self._final_status(counts)
            self.control.update_status(
                import_id=import_id,
                status=final_status,
                total_records=counts["total_records"],
                processed_records=counts["processed_records"],
                success_records=counts["success_records"],
                failed_records=counts["failed_records"],
                skipped_records=0,
            )
            self.session.commit()

            result = {
                "import_id": str(import_id),
                "status": final_status.value,
                "reprocessed_rows": load_stats.read_records,
                **counts,
                "inserted_records": load_stats.inserted_records,
                "updated_records": load_stats.updated_records,
                "load_failed_records": load_stats.failed_records,
            }
            if counts["failed_records"] > 0:
                result["error_summary"] = self.control.get_error_summary(import_id)
            return result
        except Exception as exc:
            self.session.rollback()
            self.control.update_status(
                import_id=import_id,
                status=ImportStatus.FAILED,
                error_summary=str(exc)[:1000],
            )
            self.session.commit()
            raise

    def _build_processor(self, *, processor_type: str, company_id: str | None) -> BaseProcessor:
        processor_class = PROCESSOR_CLASSES[processor_type]
        spec = get_import_spec(processor_type)
        return processor_class(
            spec=spec,
            company_id=company_id,
            staging=self.staging,
            control=self.control,
            dw=self.dw,
            batch_size=self.settings.default_batch_size,
        )

    def _processor_types(self, import_type: str) -> tuple[str, ...]:
        if import_type in {"all", "full", "pipeline"}:
            return PROCESSOR_ORDER
        if import_type not in PROCESSOR_CLASSES:
            get_import_spec(import_type)
        return (import_type,)

    def _combine_counts(self, counts_by_type: dict[str, dict[str, int]]) -> dict[str, int]:
        combined = {
            "total_records": 0,
            "processed_records": 0,
            "success_records": 0,
            "failed_records": 0,
        }
        for counts in counts_by_type.values():
            for key in combined:
                combined[key] += counts.get(key, 0)
        return combined

    def _final_status(self, counts: dict[str, int]) -> ImportStatus:
        if counts["total_records"] == 0:
            return ImportStatus.FAILED
        if counts["success_records"] > 0 and counts["failed_records"] > 0:
            return ImportStatus.PARTIAL
        if counts["success_records"] > 0 and counts["failed_records"] == 0:
            return ImportStatus.COMPLETED
        return ImportStatus.FAILED

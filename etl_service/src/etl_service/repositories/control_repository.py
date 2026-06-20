from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from etl_service.core.config import Settings
from etl_service.db.identifiers import table_identifier
from etl_service.domain.enums import ImportStatus
from etl_service.domain.models import ValidationError


class ControlRepository:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    @property
    def imports_table(self) -> str:
        return table_identifier(self.settings.control_schema, "data_imports")

    @property
    def errors_table(self) -> str:
        return table_identifier(self.settings.control_schema, "import_error_details")

    def create_import(
        self,
        *,
        company_id: str,
        import_type: str,
        source_type: str,
        original_filename: str | None,
        file_path: str | None,
        file_size_bytes: int | None,
        total_records: int,
        created_by: str | None = None,
    ) -> UUID:
        import_id = uuid4()
        self.session.execute(
            text(
                f"""
                INSERT INTO {self.imports_table} (
                    import_id,
                    company_id,
                    import_type,
                    source_type,
                    original_filename,
                    file_path,
                    file_size_bytes,
                    status,
                    total_records,
                    upload_started_at,
                    created_by
                )
                VALUES (
                    CAST(:import_id AS UUID),
                    CAST(:company_id AS UUID),
                    CAST(:import_type AS VARCHAR),
                    CAST(:source_type AS VARCHAR),
                    :original_filename,
                    :file_path,
                    :file_size_bytes,
                    CAST(:status AS VARCHAR),
                    :total_records,
                    CURRENT_TIMESTAMP,
                    CAST(:created_by AS UUID)
                )
                """
            ),
            {
                "import_id": import_id,
                "company_id": company_id,
                "import_type": import_type,
                "source_type": source_type,
                "original_filename": original_filename,
                "file_path": file_path,
                "file_size_bytes": file_size_bytes,
                "status": ImportStatus.PENDING.value,
                "total_records": total_records,
                "created_by": created_by,
            },
        )
        return import_id

    def get_import(self, import_id: str | UUID) -> dict[str, Any]:
        row = self.session.execute(
            text(
                f"""
                SELECT *
                FROM {self.imports_table}
                WHERE import_id = :import_id
                """
            ),
            {"import_id": import_id},
        ).mappings().first()
        if row is None:
            raise ValueError(f"Import not found: {import_id}")
        return dict(row)

    def update_status(
        self,
        *,
        import_id: str | UUID,
        status: ImportStatus,
        total_records: int | None = None,
        processed_records: int | None = None,
        success_records: int | None = None,
        failed_records: int | None = None,
        skipped_records: int | None = None,
        error_summary: str | None = None,
    ) -> None:
        self.session.execute(
            text(
                f"""
                UPDATE {self.imports_table}
                SET
                    status = CAST(:status AS VARCHAR),
                    total_records = COALESCE(CAST(:total_records AS INTEGER), total_records),
                    processed_records = COALESCE(
                        CAST(:processed_records AS INTEGER),
                        processed_records
                    ),
                    success_records = COALESCE(CAST(:success_records AS INTEGER), success_records),
                    failed_records = COALESCE(CAST(:failed_records AS INTEGER), failed_records),
                    skipped_records = COALESCE(CAST(:skipped_records AS INTEGER), skipped_records),
                    error_summary = COALESCE(CAST(:error_summary AS TEXT), error_summary),
                    upload_completed_at = CASE
                        WHEN CAST(:status AS VARCHAR) = 'UPLOADED' THEN CURRENT_TIMESTAMP
                        ELSE upload_completed_at
                    END,
                    processing_started_at = CASE
                        WHEN CAST(:status AS VARCHAR) = 'PROCESSING' THEN CURRENT_TIMESTAMP
                        ELSE processing_started_at
                    END,
                    processing_completed_at = CASE
                        WHEN CAST(:status AS VARCHAR) IN ('COMPLETED', 'PARTIAL', 'FAILED')
                        THEN CURRENT_TIMESTAMP
                        ELSE processing_completed_at
                    END,
                    total_duration_seconds = CASE
                        WHEN CAST(:status AS VARCHAR) IN ('COMPLETED', 'PARTIAL', 'FAILED')
                            AND upload_started_at IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - upload_started_at))::INT
                        ELSE total_duration_seconds
                    END
                WHERE import_id = CAST(:import_id AS UUID)
                """
            ),
            {
                "import_id": import_id,
                "status": status.value,
                "total_records": total_records,
                "processed_records": processed_records,
                "success_records": success_records,
                "failed_records": failed_records,
                "skipped_records": skipped_records,
                "error_summary": error_summary,
            },
        )

    def insert_errors(self, import_id: str | UUID, errors: list[ValidationError]) -> None:
        if not errors:
            return

        params = [
            {
                "error_id": uuid4(),
                "import_id": import_id,
                **error.as_dict(),
            }
            for error in errors
        ]
        self.session.execute(
            text(
                f"""
                INSERT INTO {self.errors_table} (
                    error_id,
                    import_id,
                    row_number,
                    error_type,
                    severity,
                    field_name,
                    field_value,
                    expected_format,
                    error_message,
                    suggested_fix
                )
                VALUES (
                    :error_id,
                    :import_id,
                    :row_number,
                    :error_type,
                    :severity,
                    :field_name,
                    :field_value,
                    :expected_format,
                    :error_message,
                    :suggested_fix
                )
                """
            ),
            params,
        )

    def get_error_summary(
        self,
        import_id: str | UUID,
        *,
        limit: int = 10,
    ) -> dict[str, Any]:
        total_errors = self.session.execute(
            text(
                f"""
                SELECT COUNT(*)::int
                FROM {self.errors_table}
                WHERE import_id = :import_id
                """
            ),
            {"import_id": import_id},
        ).scalar_one()

        by_type = self.session.execute(
            text(
                f"""
                SELECT error_type, COUNT(*)::int AS count
                FROM {self.errors_table}
                WHERE import_id = :import_id
                GROUP BY error_type
                ORDER BY count DESC, error_type
                """
            ),
            {"import_id": import_id},
        ).mappings()

        by_field = self.session.execute(
            text(
                f"""
                SELECT COALESCE(field_name, '(row)') AS field_name, COUNT(*)::int AS count
                FROM {self.errors_table}
                WHERE import_id = :import_id
                GROUP BY COALESCE(field_name, '(row)')
                ORDER BY count DESC, field_name
                """
            ),
            {"import_id": import_id},
        ).mappings()

        examples = self.session.execute(
            text(
                f"""
                SELECT
                    row_number,
                    error_type,
                    field_name,
                    field_value,
                    expected_format,
                    error_message,
                    suggested_fix
                FROM {self.errors_table}
                WHERE import_id = :import_id
                ORDER BY row_number, created_at
                LIMIT :limit
                """
            ),
            {"import_id": import_id, "limit": limit},
        ).mappings()

        return {
            "total_errors": total_errors,
            "by_type": [dict(row) for row in by_type],
            "by_field": [dict(row) for row in by_field],
            "examples": [dict(row) for row in examples],
        }

    def list_errors(
        self,
        import_id: str | UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        rows = self.session.execute(
            text(
                f"""
                SELECT
                    error_id::text AS error_id,
                    import_id::text AS import_id,
                    row_number,
                    error_type,
                    severity,
                    field_name,
                    field_value,
                    expected_format,
                    error_message,
                    suggested_fix,
                    created_at
                FROM {self.errors_table}
                WHERE import_id = :import_id
                ORDER BY row_number, created_at
                LIMIT :limit
                OFFSET :offset
                """
            ),
            {"import_id": import_id, "limit": limit, "offset": offset},
        ).mappings()
        return [dict(row) for row in rows]

    def count_company_errors(
        self,
        *,
        company_id: str | UUID,
        import_id: str | UUID | None = None,
        import_type: str | None = None,
    ) -> int:
        where_sql, params = self._company_errors_filters(
            company_id=company_id,
            import_id=import_id,
            import_type=import_type,
        )
        return int(
            self.session.execute(
                text(
                    f"""
                    SELECT COUNT(*)::int
                    FROM {self.errors_table} AS errors
                    JOIN {self.imports_table} AS imports
                      ON imports.import_id = errors.import_id
                    WHERE {where_sql}
                    """
                ),
                params,
            ).scalar_one()
        )

    def list_company_errors(
        self,
        *,
        company_id: str | UUID,
        import_id: str | UUID | None = None,
        import_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        where_sql, params = self._company_errors_filters(
            company_id=company_id,
            import_id=import_id,
            import_type=import_type,
        )
        params.update({"limit": limit, "offset": offset})
        rows = self.session.execute(
            text(
                f"""
                SELECT
                    errors.error_id::text AS error_id,
                    errors.import_id::text AS import_id,
                    imports.import_type,
                    errors.row_number,
                    errors.error_type,
                    errors.severity,
                    errors.field_name,
                    errors.field_value,
                    errors.expected_format,
                    errors.error_message,
                    errors.suggested_fix,
                    errors.created_at
                FROM {self.errors_table} AS errors
                JOIN {self.imports_table} AS imports
                  ON imports.import_id = errors.import_id
                WHERE {where_sql}
                ORDER BY errors.created_at DESC, errors.row_number
                LIMIT :limit
                OFFSET :offset
                """
            ),
            params,
        ).mappings()
        return [dict(row) for row in rows]

    def get_errors_by_rows(
        self,
        import_id: str | UUID,
        row_numbers: list[int],
    ) -> dict[int, list[dict[str, Any]]]:
        if not row_numbers:
            return {}

        stmt = text(
            f"""
            SELECT
                error_id::text AS error_id,
                row_number,
                error_type,
                severity,
                field_name,
                field_value,
                expected_format,
                error_message,
                suggested_fix
            FROM {self.errors_table}
            WHERE import_id = :import_id
              AND row_number IN :row_numbers
            ORDER BY row_number, created_at
            """
        ).bindparams(bindparam("row_numbers", expanding=True))
        rows = self.session.execute(
            stmt,
            {"import_id": import_id, "row_numbers": row_numbers},
        ).mappings()

        grouped: dict[int, list[dict[str, Any]]] = {}
        for row in rows:
            row_dict = dict(row)
            row_number = int(row_dict.pop("row_number"))
            grouped.setdefault(row_number, []).append(row_dict)
        return grouped

    def get_error(self, import_id: str | UUID, error_id: str | UUID) -> dict[str, Any]:
        row = self.session.execute(
            text(
                f"""
                SELECT
                    error_id::text AS error_id,
                    import_id::text AS import_id,
                    row_number,
                    error_type,
                    severity,
                    field_name,
                    field_value,
                    expected_format,
                    error_message,
                    suggested_fix,
                    created_at
                FROM {self.errors_table}
                WHERE import_id = :import_id
                  AND error_id = CAST(:error_id AS UUID)
                """
            ),
            {"import_id": import_id, "error_id": error_id},
        ).mappings().first()
        if row is None:
            raise ValueError(f"Import error not found: {error_id}")
        return dict(row)

    def get_error_by_id(self, error_id: str | UUID) -> dict[str, Any]:
        row = self.session.execute(
            text(
                f"""
                SELECT
                    errors.error_id::text AS error_id,
                    errors.import_id::text AS import_id,
                    imports.company_id::text AS company_id,
                    imports.import_type,
                    errors.row_number,
                    errors.error_type,
                    errors.severity,
                    errors.field_name,
                    errors.field_value,
                    errors.expected_format,
                    errors.error_message,
                    errors.suggested_fix,
                    errors.created_at
                FROM {self.errors_table} AS errors
                JOIN {self.imports_table} AS imports
                  ON imports.import_id = errors.import_id
                WHERE errors.error_id = CAST(:error_id AS UUID)
                """
            ),
            {"error_id": error_id},
        ).mappings().first()
        if row is None:
            raise ValueError(f"Import error not found: {error_id}")
        return dict(row)

    def delete_errors_for_rows(
        self,
        import_id: str | UUID,
        row_numbers: list[int],
    ) -> None:
        if not row_numbers:
            return

        stmt = text(
            f"""
            DELETE FROM {self.errors_table}
            WHERE import_id = :import_id
              AND row_number IN :row_numbers
            """
        ).bindparams(bindparam("row_numbers", expanding=True))
        self.session.execute(stmt, {"import_id": import_id, "row_numbers": row_numbers})

    def get_company_field_mappings(
        self,
        *,
        company_id: str | UUID,
        import_type: str,
    ) -> list[dict[str, Any]]:
        if not self._field_mappings_table_ready(
            {
                "company_id",
                "import_type",
                "source_field",
                "normalized_source_field",
                "target_field",
                "confidence",
                "source",
                "is_active",
                "last_used_at",
            }
        ):
            return []

        table = table_identifier(self.settings.control_schema, "import_field_mappings")
        rows = self.session.execute(
            text(
                f"""
                SELECT
                    source_field,
                    normalized_source_field,
                    target_field,
                    confidence,
                    source
                FROM {table}
                WHERE company_id = CAST(:company_id AS UUID)
                  AND LOWER(import_type) = LOWER(:import_type)
                  AND COALESCE(is_active, TRUE) = TRUE
                ORDER BY confidence DESC NULLS LAST, last_used_at DESC NULLS LAST
                """
            ),
            {"company_id": company_id, "import_type": import_type},
        ).mappings()
        return [dict(row) for row in rows]

    def mark_field_mapping_used(
        self,
        *,
        company_id: str | UUID,
        import_type: str,
        normalized_source_field: str,
        target_field: str,
    ) -> None:
        if not self._field_mappings_table_ready(
            {
                "company_id",
                "import_type",
                "normalized_source_field",
                "target_field",
                "last_used_at",
            }
        ):
            return

        table = table_identifier(self.settings.control_schema, "import_field_mappings")
        self.session.execute(
            text(
                f"""
                UPDATE {table}
                SET last_used_at = CURRENT_TIMESTAMP
                WHERE company_id = CAST(:company_id AS UUID)
                  AND LOWER(import_type) = LOWER(:import_type)
                  AND normalized_source_field = :normalized_source_field
                  AND target_field = :target_field
                """
            ),
            {
                "company_id": company_id,
                "import_type": import_type,
                "normalized_source_field": normalized_source_field,
                "target_field": target_field,
            },
        )

    def learn_field_mapping(
        self,
        *,
        company_id: str | UUID,
        import_type: str,
        source_field: str,
        normalized_source_field: str,
        target_field: str,
        confidence: float = 1.0,
        source: str = "manual_correction",
    ) -> None:
        if not self._field_mappings_table_ready(
            {
                "mapping_id",
                "company_id",
                "import_type",
                "source_field",
                "normalized_source_field",
                "target_field",
                "confidence",
                "source",
                "is_active",
                "created_at",
                "last_used_at",
            }
        ):
            return

        table = table_identifier(self.settings.control_schema, "import_field_mappings")
        existing = self.session.execute(
            text(
                f"""
                SELECT mapping_id
                FROM {table}
                WHERE company_id = CAST(:company_id AS UUID)
                  AND LOWER(import_type) = LOWER(:import_type)
                  AND normalized_source_field = :normalized_source_field
                  AND target_field = :target_field
                LIMIT 1
                """
            ),
            {
                "company_id": company_id,
                "import_type": import_type,
                "normalized_source_field": normalized_source_field,
                "target_field": target_field,
            },
        ).scalar_one_or_none()
        if existing:
            self.session.execute(
                text(
                    f"""
                    UPDATE {table}
                    SET
                        source_field = :source_field,
                        confidence = GREATEST(COALESCE(confidence, 0), :confidence),
                        source = :source,
                        is_active = TRUE,
                        last_used_at = CURRENT_TIMESTAMP
                    WHERE mapping_id = :mapping_id
                    """
                ),
                {
                    "mapping_id": existing,
                    "source_field": source_field,
                    "confidence": confidence,
                    "source": source,
                },
            )
            return

        self.session.execute(
            text(
                f"""
                INSERT INTO {table} (
                    mapping_id,
                    company_id,
                    import_type,
                    source_field,
                    normalized_source_field,
                    target_field,
                    confidence,
                    source,
                    is_active,
                    created_at,
                    last_used_at
                )
                VALUES (
                    :mapping_id,
                    CAST(:company_id AS UUID),
                    :import_type,
                    :source_field,
                    :normalized_source_field,
                    :target_field,
                    :confidence,
                    :source,
                    TRUE,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "mapping_id": uuid4(),
                "company_id": company_id,
                "import_type": import_type,
                "source_field": source_field,
                "normalized_source_field": normalized_source_field,
                "target_field": target_field,
                "confidence": confidence,
                "source": source,
            },
        )

    def insert_mapping_traces(
        self,
        *,
        import_id: str | UUID,
        row_number: int,
        import_type: str,
        traces: list[dict[str, Any]],
        warnings: list[dict[str, Any]],
    ) -> None:
        if not self._mapping_traces_table_ready():
            return

        table = table_identifier(self.settings.control_schema, "import_mapping_traces")
        params: list[dict[str, Any]] = []
        for trace in traces:
            params.append(
                {
                    "trace_id": uuid4(),
                    "import_id": import_id,
                    "row_number": row_number,
                    "import_type": import_type,
                    "target_field": trace.get("target_field"),
                    "source_field": trace.get("source_field"),
                    "source_value": _string_value(trace.get("source_value")),
                    "final_value": _string_value(trace.get("final_value")),
                    "rule": trace.get("rule"),
                    "confidence": trace.get("confidence"),
                    "warning": trace.get("warning"),
                }
            )

        for warning in warnings:
            params.append(
                {
                    "trace_id": uuid4(),
                    "import_id": import_id,
                    "row_number": row_number,
                    "import_type": import_type,
                    "target_field": warning.get("field_name"),
                    "source_field": None,
                    "source_value": None,
                    "final_value": None,
                    "rule": warning.get("warning_type"),
                    "confidence": None,
                    "warning": warning.get("message"),
                }
            )

        if not params:
            return

        self.session.execute(
            text(
                f"""
                INSERT INTO {table} (
                    trace_id,
                    import_id,
                    row_number,
                    import_type,
                    target_field,
                    source_field,
                    source_value,
                    final_value,
                    rule,
                    confidence,
                    warning,
                    created_at
                )
                VALUES (
                    :trace_id,
                    CAST(:import_id AS UUID),
                    :row_number,
                    :import_type,
                    :target_field,
                    :source_field,
                    :source_value,
                    :final_value,
                    :rule,
                    :confidence,
                    :warning,
                    CURRENT_TIMESTAMP
                )
                """
            ),
            params,
        )

    def _company_errors_filters(
        self,
        *,
        company_id: str | UUID,
        import_id: str | UUID | None,
        import_type: str | None,
    ) -> tuple[str, dict[str, Any]]:
        filters = ["imports.company_id = CAST(:company_id AS UUID)"]
        params: dict[str, Any] = {"company_id": company_id}

        if import_id is not None:
            filters.append("imports.import_id = CAST(:import_id AS UUID)")
            params["import_id"] = import_id

        if import_type:
            filters.append("LOWER(imports.import_type) = LOWER(:import_type)")
            params["import_type"] = import_type

        return " AND ".join(filters), params

    def _control_table_exists(self, table_name: str) -> bool:
        row = self.session.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = :schema
                  AND table_name = :table_name
                LIMIT 1
                """
            ),
            {"schema": self.settings.control_schema, "table_name": table_name},
        ).scalar_one_or_none()
        return row is not None

    def _field_mappings_table_ready(self, required_columns: set[str]) -> bool:
        if not self._control_table_exists("import_field_mappings"):
            return False

        rows = self.session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema
                  AND table_name = 'import_field_mappings'
                """
            ),
            {"schema": self.settings.control_schema},
        ).scalars()
        columns = {str(row) for row in rows}
        return required_columns.issubset(columns)

    def _mapping_traces_table_ready(self) -> bool:
        required_columns = {
            "trace_id",
            "import_id",
            "row_number",
            "import_type",
            "target_field",
            "source_field",
            "source_value",
            "final_value",
            "rule",
            "confidence",
            "warning",
            "created_at",
        }
        if not self._control_table_exists("import_mapping_traces"):
            return False

        rows = self.session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema
                  AND table_name = 'import_mapping_traces'
                """
            ),
            {"schema": self.settings.control_schema},
        ).scalars()
        columns = {str(row) for row in rows}
        return required_columns.issubset(columns)


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)

import json
import math
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from etl_service.core.config import Settings
from etl_service.db.identifiers import quote_identifier, table_identifier
from etl_service.domain.models import ExtractedRow, ImportSpec, ValidationError


class StagingRepository:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self._json_column_types: dict[tuple[str, str], str] = {}
        self._staging_pk_columns: dict[str, str] = {}

    def bulk_insert_rows(
        self,
        *,
        import_id: str,
        spec: ImportSpec,
        rows: list[ExtractedRow],
    ) -> int:
        if not rows:
            return 0

        table = table_identifier(self.settings.staging_schema, spec.staging_table)
        raw_data_expr = self._json_cast(spec=spec, column="raw_data", param="raw_data")
        params = [
            {
                "import_id": import_id,
                "row_number": row.row_number,
                "raw_data": _to_json_param(row.raw_data),
            }
            for row in rows
        ]
        stmt = text(
            f"""
            INSERT INTO {table} (
                import_id,
                row_number,
                raw_data,
                is_processed,
                is_valid,
                created_at
            )
            VALUES (
                :import_id,
                :row_number,
                {raw_data_expr},
                FALSE,
                FALSE,
                CURRENT_TIMESTAMP
            )
            """
        )
        self.session.execute(stmt, params)
        return len(rows)

    def fetch_rows_for_validation(
        self,
        *,
        import_id: str,
        spec: ImportSpec,
        limit: int,
    ) -> list[dict[str, Any]]:
        table = table_identifier(self.settings.staging_schema, spec.staging_table)
        pk = quote_identifier(self._staging_pk(spec))
        rows = self.session.execute(
            text(
                f"""
                SELECT
                    {pk} AS staging_id,
                    row_number,
                    raw_data
                FROM {table}
                WHERE import_id = :import_id
                  AND is_processed = FALSE
                  AND is_valid = FALSE
                ORDER BY row_number
                LIMIT :limit
                """
            ),
            {"import_id": import_id, "limit": limit},
        ).mappings()
        return [dict(row) for row in rows]

    def fetch_pending_rows(
        self,
        *,
        import_id: str,
        spec: ImportSpec,
        limit: int,
    ) -> list[dict[str, Any]]:
        table = table_identifier(self.settings.staging_schema, spec.staging_table)
        pk = quote_identifier(self._staging_pk(spec))
        rows = self.session.execute(
            text(
                f"""
                SELECT
                    {pk} AS staging_id,
                    row_number,
                    raw_data
                FROM {table}
                WHERE import_id = :import_id
                  AND is_processed = FALSE
                ORDER BY row_number
                LIMIT :limit
                """
            ),
            {"import_id": import_id, "limit": limit},
        ).mappings()
        return [dict(row) for row in rows]

    def fetch_pending_rows_by_ids(
        self,
        *,
        import_id: str,
        spec: ImportSpec,
        staging_ids: list[str],
    ) -> list[dict[str, Any]]:
        if not staging_ids:
            return []

        table = table_identifier(self.settings.staging_schema, spec.staging_table)
        pk_name = self._staging_pk(spec)
        pk = quote_identifier(pk_name)
        stmt = text(
            f"""
            SELECT
                {pk} AS staging_id,
                row_number,
                raw_data
            FROM {table}
            WHERE import_id = :import_id
              AND {pk} IN :staging_ids
              AND is_processed = FALSE
            ORDER BY row_number
            """
        ).bindparams(bindparam("staging_ids", expanding=True))
        rows = self.session.execute(
            stmt,
            {"import_id": import_id, "staging_ids": staging_ids},
        ).mappings()
        return [dict(row) for row in rows]

    def fetch_failed_rows(
        self,
        *,
        import_id: str,
        spec: ImportSpec,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        table = table_identifier(self.settings.staging_schema, spec.staging_table)
        pk = quote_identifier(self._staging_pk(spec))
        rows = self.session.execute(
            text(
                f"""
                SELECT
                    {pk} AS staging_id,
                    row_number,
                    raw_data,
                    clean_data,
                    validation_errors
                FROM {table}
                WHERE import_id = :import_id
                  AND is_processed = TRUE
                  AND is_valid = FALSE
                ORDER BY row_number
                LIMIT :limit
                OFFSET :offset
                """
            ),
            {"import_id": import_id, "limit": limit, "offset": offset},
        ).mappings()
        return [dict(row) for row in rows]

    def count_failed_rows(self, *, import_id: str, spec: ImportSpec) -> int:
        table = table_identifier(self.settings.staging_schema, spec.staging_table)
        return int(
            self.session.execute(
                text(
                    f"""
                    SELECT COUNT(*)::int
                    FROM {table}
                    WHERE import_id = :import_id
                      AND is_processed = TRUE
                      AND is_valid = FALSE
                    """
                ),
                {"import_id": import_id},
            ).scalar_one()
        )

    def get_row_by_row_number(
        self,
        *,
        import_id: str,
        spec: ImportSpec,
        row_number: int,
    ) -> dict[str, Any] | None:
        table = table_identifier(self.settings.staging_schema, spec.staging_table)
        pk = quote_identifier(self._staging_pk(spec))
        row = self.session.execute(
            text(
                f"""
                SELECT
                    {pk} AS staging_id,
                    row_number,
                    raw_data,
                    clean_data,
                    validation_errors,
                    is_valid,
                    is_processed
                FROM {table}
                WHERE import_id = :import_id
                  AND row_number = :row_number
                LIMIT 1
                """
            ),
            {"import_id": import_id, "row_number": row_number},
        ).mappings().first()
        return dict(row) if row else None

    def get_row_by_staging_id(
        self,
        *,
        import_id: str,
        spec: ImportSpec,
        staging_id: str,
    ) -> dict[str, Any] | None:
        table = table_identifier(self.settings.staging_schema, spec.staging_table)
        pk = quote_identifier(self._staging_pk(spec))
        row = self.session.execute(
            text(
                f"""
                SELECT
                    {pk} AS staging_id,
                    row_number,
                    raw_data,
                    clean_data,
                    validation_errors,
                    is_valid,
                    is_processed
                FROM {table}
                WHERE import_id = :import_id
                  AND {pk} = :staging_id
                LIMIT 1
                """
            ),
            {"import_id": import_id, "staging_id": staging_id},
        ).mappings().first()
        return dict(row) if row else None

    def save_validation_result(
        self,
        *,
        spec: ImportSpec,
        staging_id: str,
        clean_data: dict[str, Any],
        errors: list[ValidationError],
    ) -> None:
        table = table_identifier(self.settings.staging_schema, spec.staging_table)
        pk = quote_identifier(self._staging_pk(spec))
        is_valid = not errors
        validation_errors = [error.as_dict() for error in errors] if errors else None
        is_processed = not is_valid
        clean_data_expr = self._json_cast(spec=spec, column="clean_data", param="clean_data")
        validation_errors_expr = self._json_cast(
            spec=spec,
            column="validation_errors",
            param="validation_errors",
        )

        stmt = text(
            f"""
            UPDATE {table}
            SET
                clean_data = {clean_data_expr},
                validation_errors = {validation_errors_expr},
                is_valid = :is_valid,
                is_processed = :is_processed,
                processed_at = CASE
                    WHEN :is_processed THEN CURRENT_TIMESTAMP
                    ELSE processed_at
                END
            WHERE {pk} = :staging_id
            """
        )
        self.session.execute(
            stmt,
            {
                "staging_id": staging_id,
                "clean_data": _to_json_param(clean_data),
                "validation_errors": _to_json_param(validation_errors),
                "is_valid": is_valid,
                "is_processed": is_processed,
            },
        )

    def fetch_valid_rows_for_load(
        self,
        *,
        import_id: str,
        spec: ImportSpec,
        limit: int,
    ) -> list[dict[str, Any]]:
        table = table_identifier(self.settings.staging_schema, spec.staging_table)
        pk = quote_identifier(self._staging_pk(spec))
        rows = self.session.execute(
            text(
                f"""
                SELECT
                    {pk} AS staging_id,
                    row_number,
                    clean_data
                FROM {table}
                WHERE import_id = :import_id
                  AND is_valid = TRUE
                  AND is_processed = FALSE
                ORDER BY row_number
                LIMIT :limit
                """
            ),
            {"import_id": import_id, "limit": limit},
        ).mappings()
        return [dict(row) for row in rows]

    def mark_loaded(self, *, spec: ImportSpec, staging_id: str) -> None:
        table = table_identifier(self.settings.staging_schema, spec.staging_table)
        pk = quote_identifier(self._staging_pk(spec))
        self.session.execute(
            text(
                f"""
                UPDATE {table}
                SET is_processed = TRUE,
                    processed_at = CURRENT_TIMESTAMP
                WHERE {pk} = :staging_id
                """
            ),
            {"staging_id": staging_id},
        )

    def mark_failed(
        self,
        *,
        spec: ImportSpec,
        staging_id: str,
        errors: list[ValidationError],
    ) -> None:
        table = table_identifier(self.settings.staging_schema, spec.staging_table)
        pk = quote_identifier(self._staging_pk(spec))
        validation_errors_expr = self._json_cast(
            spec=spec,
            column="validation_errors",
            param="validation_errors",
        )
        stmt = text(
            f"""
            UPDATE {table}
            SET
                is_valid = FALSE,
                is_processed = TRUE,
                validation_errors = {validation_errors_expr},
                processed_at = CURRENT_TIMESTAMP
            WHERE {pk} = :staging_id
            """
        )
        self.session.execute(
            stmt,
            {
                "staging_id": staging_id,
                "validation_errors": _to_json_param([error.as_dict() for error in errors]),
            },
        )

    def mark_processed(
        self,
        *,
        spec: ImportSpec,
        staging_id: str,
        clean_data: dict[str, Any],
        errors: list[ValidationError],
    ) -> None:
        table = table_identifier(self.settings.staging_schema, spec.staging_table)
        pk = quote_identifier(self._staging_pk(spec))
        is_valid = not errors
        clean_data_expr = self._json_cast(spec=spec, column="clean_data", param="clean_data")
        validation_errors_expr = self._json_cast(
            spec=spec,
            column="validation_errors",
            param="validation_errors",
        )
        validation_errors = [error.as_dict() for error in errors] if errors else None
        stmt = text(
            f"""
            UPDATE {table}
            SET
                clean_data = {clean_data_expr},
                validation_errors = {validation_errors_expr},
                is_valid = :is_valid,
                is_processed = TRUE,
                processed_at = CURRENT_TIMESTAMP
            WHERE {pk} = :staging_id
            """
        )
        self.session.execute(
            stmt,
            {
                "staging_id": staging_id,
                "clean_data": _to_json_param(clean_data),
                "validation_errors": _to_json_param(validation_errors),
                "is_valid": is_valid,
            },
        )

    def apply_correction(
        self,
        *,
        spec: ImportSpec,
        staging_id: str,
        corrected_data: dict[str, Any],
    ) -> None:
        table = table_identifier(self.settings.staging_schema, spec.staging_table)
        pk = quote_identifier(self._staging_pk(spec))
        raw_data_expr = self._json_cast(spec=spec, column="raw_data", param="raw_data")
        clean_data_expr = self._json_cast(spec=spec, column="clean_data", param="clean_data")
        validation_errors_expr = self._json_cast(
            spec=spec,
            column="validation_errors",
            param="validation_errors",
        )
        self.session.execute(
            text(
                f"""
                UPDATE {table}
                SET
                    raw_data = {raw_data_expr},
                    clean_data = {clean_data_expr},
                    validation_errors = {validation_errors_expr},
                    is_valid = FALSE,
                    is_processed = FALSE,
                    processed_at = NULL
                WHERE {pk} = :staging_id
                """
            ),
            {
                "staging_id": staging_id,
                "raw_data": _to_json_param(corrected_data),
                "clean_data": _to_json_param(corrected_data),
                "validation_errors": None,
            },
        )

    def reopen_rows(self, *, spec: ImportSpec, staging_ids: list[str]) -> None:
        if not staging_ids:
            return

        table = table_identifier(self.settings.staging_schema, spec.staging_table)
        pk = quote_identifier(self._staging_pk(spec))
        validation_errors_expr = self._json_cast(
            spec=spec,
            column="validation_errors",
            param="validation_errors",
        )
        stmt = text(
            f"""
            UPDATE {table}
            SET
                validation_errors = {validation_errors_expr},
                is_valid = FALSE,
                is_processed = FALSE,
                processed_at = NULL
            WHERE {pk} IN :staging_ids
            """
        ).bindparams(bindparam("staging_ids", expanding=True))
        self.session.execute(stmt, {"staging_ids": staging_ids, "validation_errors": None})

    def count_states(self, *, import_id: str, spec: ImportSpec) -> dict[str, int]:
        table = table_identifier(self.settings.staging_schema, spec.staging_table)
        row = self.session.execute(
            text(
                f"""
                SELECT
                    COUNT(*)::int AS total_records,
                    COUNT(*) FILTER (WHERE is_processed = TRUE)::int AS processed_records,
                    COUNT(*) FILTER (WHERE is_processed = TRUE AND is_valid = TRUE)::int AS success_records,
                    COUNT(*) FILTER (WHERE is_processed = TRUE AND is_valid = FALSE)::int AS failed_records
                FROM {table}
                WHERE import_id = :import_id
                """
            ),
            {"import_id": import_id},
        ).mappings().one()
        return dict(row)

    def _staging_pk(self, spec: ImportSpec) -> str:
        if spec.staging_table in self._staging_pk_columns:
            return self._staging_pk_columns[spec.staging_table]

        configured_pk = self._column_exists(spec=spec, column=spec.staging_pk)
        if configured_pk:
            self._staging_pk_columns[spec.staging_table] = spec.staging_pk
            return spec.staging_pk

        detected_pk = self._primary_key_column(spec)
        if detected_pk:
            self._staging_pk_columns[spec.staging_table] = detected_pk
            return detected_pk

        fallback_pk = self._fallback_pk_column(spec)
        if fallback_pk:
            self._staging_pk_columns[spec.staging_table] = fallback_pk
            return fallback_pk

        columns = ", ".join(self._table_columns(spec))
        raise ValueError(
            f"Could not detect primary key for staging table "
            f"{self.settings.staging_schema}.{spec.staging_table}. "
            f"Configured column {spec.staging_pk!r} does not exist. "
            f"Available columns: {columns}"
        )

    def _column_exists(self, *, spec: ImportSpec, column: str) -> bool:
        row = self.session.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = :schema
                  AND table_name = :table
                  AND column_name = :column
                LIMIT 1
                """
            ),
            {
                "schema": self.settings.staging_schema,
                "table": spec.staging_table,
                "column": column,
            },
        ).scalar_one_or_none()
        return row is not None

    def _primary_key_column(self, spec: ImportSpec) -> str | None:
        row = self.session.execute(
            text(
                """
                SELECT kcu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                 AND tc.table_name = kcu.table_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = :schema
                  AND tc.table_name = :table
                ORDER BY kcu.ordinal_position
                LIMIT 1
                """
            ),
            {
                "schema": self.settings.staging_schema,
                "table": spec.staging_table,
            },
        ).scalar_one_or_none()
        return str(row) if row else None

    def _fallback_pk_column(self, spec: ImportSpec) -> str | None:
        columns = set(self._table_columns(spec))
        candidates = (
            "staging_id",
            "id",
            f"{spec.staging_table}_id",
            f"{spec.import_type}_staging_id",
        )
        for candidate in candidates:
            if candidate in columns:
                return candidate
        return None

    def _table_columns(self, spec: ImportSpec) -> list[str]:
        rows = self.session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema
                  AND table_name = :table
                ORDER BY ordinal_position
                """
            ),
            {
                "schema": self.settings.staging_schema,
                "table": spec.staging_table,
            },
        ).scalars()
        return [str(row) for row in rows]

    def _json_cast(self, *, spec: ImportSpec, column: str, param: str) -> str:
        json_type = self._json_column_type(spec=spec, column=column)
        return f"CAST(:{param} AS {json_type.upper()})"

    def _json_column_type(self, *, spec: ImportSpec, column: str) -> str:
        key = (spec.staging_table, column)
        if key in self._json_column_types:
            return self._json_column_types[key]

        row = self.session.execute(
            text(
                """
                SELECT udt_name
                FROM information_schema.columns
                WHERE table_schema = :schema
                  AND table_name = :table
                  AND column_name = :column
                LIMIT 1
                """
            ),
            {
                "schema": self.settings.staging_schema,
                "table": spec.staging_table,
                "column": column,
            },
        ).scalar_one_or_none()
        json_type = "jsonb" if row == "jsonb" else "json"
        self._json_column_types[key] = json_type
        return json_type


def _to_json_param(value: Any) -> str | None:
    if value is None:
        return None
    normalized = _normalize_json_value(value)
    return json.dumps(normalized, ensure_ascii=True, allow_nan=False, default=str)


def _normalize_json_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {
            str(key): _normalize_json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [_normalize_json_value(item) for item in value]
    return value

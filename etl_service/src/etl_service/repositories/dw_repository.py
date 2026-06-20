from difflib import SequenceMatcher
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from etl_service.core.config import Settings
from etl_service.db.identifiers import quote_identifier, table_identifier
from etl_service.domain.models import ImportSpec


class DwRepository:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self._table_columns_cache: dict[str, set[str]] = {}

    def company_exists(self, company_id: str) -> bool:
        table = table_identifier(self.settings.dw_schema, "companies")
        row = self.session.execute(
            text(f"SELECT 1 FROM {table} WHERE company_id = :company_id LIMIT 1"),
            {"company_id": company_id},
        ).scalar_one_or_none()
        return row is not None

    def record_exists(self, *, table_name: str, pk_column: str, value: Any) -> bool:
        if value in (None, ""):
            return False
        table = table_identifier(self.settings.dw_schema, table_name)
        pk = quote_identifier(pk_column)
        row = self.session.execute(
            text(
                f"""
                SELECT 1
                FROM {table}
                WHERE TRIM(CAST({pk} AS TEXT)) = TRIM(CAST(:value AS TEXT))
                LIMIT 1
                """
            ),
            {"value": value},
        ).scalar_one_or_none()
        return row is not None

    def find_record_id_by_value(
        self,
        *,
        table_name: str,
        pk_column: str,
        value: Any,
        company_id: str | None = None,
    ) -> str | None:
        if value in (None, ""):
            return None

        if self.record_exists(table_name=table_name, pk_column=pk_column, value=value):
            return str(value)

        columns = self._table_columns(table_name)
        lookup_columns = list(dict.fromkeys(
            column
            for column in self._lookup_columns(table_name)
            if column in columns and column != pk_column
        ))
        if not lookup_columns:
            return None

        company_filter = ""
        params: dict[str, Any] = {"value": str(value).strip()}
        company_column = self._company_column(columns)
        if company_id and company_column:
            company_filter = f" AND {quote_identifier(company_column)} = CAST(:company_id AS UUID)"
            params["company_id"] = company_id

        table = table_identifier(self.settings.dw_schema, table_name)
        pk = quote_identifier(pk_column)
        for column in lookup_columns:
            quoted_column = quote_identifier(column)
            row = self.session.execute(
                text(
                    f"""
                    SELECT {pk}
                    FROM {table}
                    WHERE LOWER(TRIM(CAST({quoted_column} AS TEXT))) = LOWER(TRIM(:value))
                    {company_filter}
                    LIMIT 1
                    """
                ),
                params,
            ).scalar_one_or_none()
            if row:
                return str(row)
        return None

    def find_similar_record_id_by_value(
        self,
        *,
        table_name: str,
        pk_column: str,
        value: Any,
        company_id: str | None = None,
        min_score: float = 0.92,
    ) -> tuple[str, float, str] | None:
        if value in (None, ""):
            return None

        columns = self._table_columns(table_name)
        lookup_columns = list(dict.fromkeys(
            column
            for column in self._lookup_columns(table_name)
            if column in columns and column != pk_column
        ))
        if not lookup_columns:
            return None

        company_filter = ""
        params: dict[str, Any] = {}
        company_column = self._company_column(columns)
        if company_id and company_column:
            company_filter = f" WHERE {quote_identifier(company_column)} = CAST(:company_id AS UUID)"
            params["company_id"] = company_id

        table = table_identifier(self.settings.dw_schema, table_name)
        pk = quote_identifier(pk_column)
        selected_columns = ", ".join(quote_identifier(column) for column in lookup_columns)
        rows = self.session.execute(
            text(
                f"""
                SELECT {pk} AS record_id, {selected_columns}
                FROM {table}
                {company_filter}
                LIMIT 500
                """
            ),
            params,
        ).mappings()

        expected = _semantic_text(value)
        best_id: str | None = None
        best_column = ""
        best_score = 0.0
        for row in rows:
            for column in lookup_columns:
                candidate = row.get(column)
                if candidate in (None, ""):
                    continue
                score = SequenceMatcher(None, expected, _semantic_text(candidate)).ratio()
                if score > best_score:
                    best_id = str(row["record_id"])
                    best_column = column
                    best_score = score

        if best_id and best_score >= min_score:
            return best_id, round(best_score, 4), best_column
        return None

    def upsert_clean_row(self, *, spec: ImportSpec, clean_data: dict[str, Any]) -> tuple[str, str]:
        payload = self._payload_for_spec(spec, clean_data)
        existing_id = self._find_existing_id(spec, payload)

        if existing_id:
            payload[spec.dw_pk] = existing_id
            self._update_row(spec, payload)
            return str(existing_id), "updated"

        payload.setdefault(spec.dw_pk, str(uuid4()))
        self._insert_row(spec, payload)
        return str(payload[spec.dw_pk]), "inserted"

    def _payload_for_spec(self, spec: ImportSpec, clean_data: dict[str, Any]) -> dict[str, Any]:
        return {column: clean_data[column] for column in spec.columns if column in clean_data}

    def _find_existing_id(self, spec: ImportSpec, payload: dict[str, Any]) -> Any | None:
        table = table_identifier(self.settings.dw_schema, spec.dw_table)
        pk = quote_identifier(spec.dw_pk)

        if payload.get(spec.dw_pk):
            row = self.session.execute(
                text(f"SELECT {pk} FROM {table} WHERE {pk} = :pk_value LIMIT 1"),
                {"pk_value": payload[spec.dw_pk]},
            ).scalar_one_or_none()
            if row:
                return row

        for lookup_group in spec.lookup_groups:
            if not all(payload.get(field) not in (None, "") for field in lookup_group):
                continue

            conditions = " AND ".join(
                f"{quote_identifier(field)} = :lookup_{index}"
                for index, field in enumerate(lookup_group)
            )
            params = {
                f"lookup_{index}": payload[field]
                for index, field in enumerate(lookup_group)
            }
            row = self.session.execute(
                text(f"SELECT {pk} FROM {table} WHERE {conditions} LIMIT 1"),
                params,
            ).scalar_one_or_none()
            if row:
                return row

        return None

    def _table_columns(self, table_name: str) -> set[str]:
        if table_name in self._table_columns_cache:
            return self._table_columns_cache[table_name]

        rows = self.session.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema
                  AND table_name = :table_name
                """
            ),
            {"schema": self.settings.dw_schema, "table_name": table_name},
        ).scalars()
        columns = {str(row) for row in rows}
        self._table_columns_cache[table_name] = columns
        return columns

    def _company_column(self, columns: set[str]) -> str | None:
        for column in ("company_id", "company_id_fk"):
            if column in columns:
                return column
        return None

    def _lookup_columns(self, table_name: str) -> tuple[str, ...]:
        table_specific = {
            "branches": ("code", "name", "city"),
            "categories": ("name", "code", "description"),
            "customers": ("tax_id", "erp_customer_code", "name", "contact_email"),
            "inventory": ("sku", "product_code", "name"),
            "products": ("sku", "erp_product_code", "barcode", "name"),
            "purchases": ("purchase_order_number", "invoice_number"),
            "sales": ("invoice_number", "sales_number"),
            "suppliers": ("erp_supplier_code", "tax_id", "name"),
        }
        generic = (
            "code",
            "sku",
            "name",
            "tax_id",
            "barcode",
            "erp_product_code",
            "erp_supplier_code",
            "erp_customer_code",
            "invoice_number",
            "purchase_order_number",
        )
        return table_specific.get(table_name, generic) + generic

    def _insert_row(self, spec: ImportSpec, payload: dict[str, Any]) -> None:
        table = table_identifier(self.settings.dw_schema, spec.dw_table)
        columns = list(payload.keys())
        quoted_columns = ", ".join(quote_identifier(column) for column in columns)
        values = ", ".join(f":{column}" for column in columns)
        self.session.execute(
            text(f"INSERT INTO {table} ({quoted_columns}) VALUES ({values})"),
            payload,
        )

    def _update_row(self, spec: ImportSpec, payload: dict[str, Any]) -> None:
        table = table_identifier(self.settings.dw_schema, spec.dw_table)
        update_columns = [
            column
            for column in payload
            if column != spec.dw_pk and column not in {"created_at", "created_by"}
        ]
        if not update_columns:
            return

        assignments = ", ".join(
            f"{quote_identifier(column)} = :{column}"
            for column in update_columns
        )
        pk = quote_identifier(spec.dw_pk)
        self.session.execute(
            text(f"UPDATE {table} SET {assignments} WHERE {pk} = :{spec.dw_pk}"),
            payload,
        )


def _semantic_text(value: Any) -> str:
    return " ".join(str(value).strip().lower().replace("-", " ").replace("_", " ").split())

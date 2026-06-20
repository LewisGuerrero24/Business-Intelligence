from __future__ import annotations

from typing import Any

from etl_service.etl.preclean.header_normalizer import compact_field_name
from etl_service.etl.preclean.models import (
    FieldTrace,
    InterpretationWarning,
    RelationshipResult,
)
from etl_service.repositories.dw_repository import DwRepository


RELATION_ALIASES: dict[str, tuple[str, ...]] = {
    "branch": ("branch", "branch_name", "branch_code", "sucursal", "sede", "codigo_sede"),
    "category": ("category", "category_name", "categoria", "nombre_categoria"),
    "customer": ("customer", "customer_name", "cliente", "nombre_cliente", "nit", "tax_id"),
    "inventory": ("inventory", "inventario", "sku", "producto", "product"),
    "product": ("product", "product_name", "producto", "sku", "codigo_producto", "referencia"),
    "purchase": ("purchase", "purchase_order_number", "compra", "orden_compra"),
    "sales": ("sales", "sale", "venta", "invoice_number", "factura"),
    "supplier": ("supplier", "supplier_name", "proveedor", "nombre_proveedor", "nit"),
}


class RelationshipResolver:
    def __init__(self, dw: DwRepository) -> None:
        self.dw = dw

    def resolve(
        self,
        *,
        data: dict[str, Any],
        company_id: str | None,
        relation_rules: tuple[Any, ...],
    ) -> RelationshipResult:
        resolved = dict(data)
        traces: list[FieldTrace] = []
        warnings: list[InterpretationWarning] = []
        confidence: dict[str, float] = {}

        for relation in relation_rules:
            current_value = resolved.get(relation.field_name)
            if self.dw.record_exists(
                table_name=relation.table_name,
                pk_column=relation.pk_column,
                value=current_value,
            ):
                confidence[relation.field_name] = 1.0
                continue

            lookup_value, source_field = self._relation_lookup_value(
                data=resolved,
                relation_field=relation.field_name,
            )
            if current_value not in (None, ""):
                lookup_value = current_value
                source_field = relation.field_name
            if lookup_value in (None, ""):
                continue

            found_id = self.dw.find_record_id_by_value(
                table_name=relation.table_name,
                pk_column=relation.pk_column,
                value=lookup_value,
                company_id=company_id,
            )
            if found_id:
                resolved[relation.field_name] = found_id
                confidence[relation.field_name] = 0.96
                traces.append(
                    FieldTrace(
                        target_field=relation.field_name,
                        source_field=source_field,
                        source_value=lookup_value,
                        final_value=found_id,
                        rule="relationship_resolved",
                        confidence=0.96,
                    )
                )
                continue

            similar = self.dw.find_similar_record_id_by_value(
                table_name=relation.table_name,
                pk_column=relation.pk_column,
                value=lookup_value,
                company_id=company_id,
                min_score=0.92,
            )
            if similar:
                found_id, score, matched_column = similar
                resolved[relation.field_name] = found_id
                confidence[relation.field_name] = score
                traces.append(
                    FieldTrace(
                        target_field=relation.field_name,
                        source_field=source_field,
                        source_value=lookup_value,
                        final_value=found_id,
                        rule="semantic_relation_lookup",
                        confidence=score,
                        warning=f"Resolved by semantic match against {matched_column}.",
                    )
                )
            else:
                warnings.append(
                    InterpretationWarning(
                        field_name=relation.field_name,
                        warning_type="RELATION_NOT_RESOLVED",
                        message=(
                            f"Could not resolve {relation.field_name} in "
                            f"{relation.table_name} by UUID, code, name or available lookup fields."
                        ),
                    )
                )

        return RelationshipResult(
            resolved_data=resolved,
            mapping_trace=traces,
            warnings=warnings,
            confidence=confidence,
        )

    def _relation_lookup_value(
        self,
        *,
        data: dict[str, Any],
        relation_field: str,
    ) -> tuple[Any, str]:
        relation_name = self._relation_name(relation_field)
        candidate_fields = (
            relation_name,
            f"{relation_name}_name",
            f"{relation_name}_code",
            f"{relation_name}_number",
            f"erp_{relation_name}_code",
            *RELATION_ALIASES.get(relation_name, ()),
        )
        for candidate in candidate_fields:
            normalized_candidate = compact_field_name(candidate)
            value = data.get(normalized_candidate)
            if value not in (None, ""):
                return value, normalized_candidate

        relation_tokens = set(compact_field_name(alias) for alias in RELATION_ALIASES.get(relation_name, ()))
        relation_tokens.add(relation_name)
        for field_name, value in data.items():
            if value in (None, ""):
                continue
            normalized_field = compact_field_name(field_name)
            field_tokens = set(normalized_field.split("_"))
            if relation_tokens.intersection(field_tokens):
                return value, normalized_field
        return None, relation_field

    def _relation_name(self, field_name: str) -> str:
        normalized = compact_field_name(field_name)
        for suffix in ("_id_fk", "_fk", "_id"):
            if normalized.endswith(suffix):
                return normalized[: -len(suffix)]
        return normalized

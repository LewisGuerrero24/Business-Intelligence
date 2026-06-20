from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from etl_service.etl.preclean.header_normalizer import compact_field_name


CONTEXT_SYNONYMS: dict[str, tuple[str, ...]] = {
    "address": ("direccion", "ubicacion", "domicilio"),
    "barcode": ("ean", "codigo_barras", "barras"),
    "branch": ("branch", "sucursal", "sede", "local", "punto_venta"),
    "category": ("category", "categoria", "linea", "familia"),
    "code": ("code", "codigo", "cod", "referencia", "numero"),
    "contact": ("contact", "contacto"),
    "customer": ("customer", "cliente", "comprador"),
    "date": ("date", "fecha"),
    "description": ("description", "descripcion", "detalle"),
    "email": ("email", "correo", "mail"),
    "mobile": ("mobile", "celular", "movil"),
    "name": ("name", "nombre", "razon_social"),
    "phone": ("phone", "telefono", "tel"),
    "product": ("product", "producto", "item", "articulo"),
    "purchase": ("purchase", "compra", "orden"),
    "sale": ("sale", "venta", "factura"),
    "sku": ("sku", "referencia", "codigo_producto"),
    "supplier": ("supplier", "proveedor", "vendor"),
    "tax": ("tax", "nit", "documento", "identificacion", "id_fiscal"),
}


class ContextualFieldMapper:
    def target_for(
        self,
        *,
        normalized_source: str,
        field_rules: dict[str, Any],
    ) -> tuple[str | None, str, float]:
        source_tokens = set(normalized_source.split("_"))
        best_field: str | None = None
        best_score = 0.0

        for field_name, rule in field_rules.items():
            field_tokens = self._field_tokens(field_name, rule)
            overlap_score = self._overlap_score(source_tokens, field_tokens)
            similarity_score = self._similarity_score(normalized_source, field_name, rule)
            score = max(overlap_score, similarity_score)
            if score > best_score:
                best_field = field_name
                best_score = score

        if best_field and best_score >= 0.62:
            rule_name = "contextual_match" if best_score >= 0.74 else "similarity_match"
            return best_field, rule_name, best_score
        return None, "unmapped", 0.0

    def _field_tokens(self, field_name: str, rule: Any) -> set[str]:
        tokens = set(compact_field_name(field_name).split("_"))
        for alias in getattr(rule, "aliases", ()):
            tokens.update(compact_field_name(alias).split("_"))
        expanded = set(tokens)
        for token in tokens:
            expanded.update(CONTEXT_SYNONYMS.get(token, ()))
        return expanded

    def _overlap_score(self, source_tokens: set[str], field_tokens: set[str]) -> float:
        if not source_tokens or not field_tokens:
            return 0.0
        matches = source_tokens.intersection(field_tokens)
        if not matches:
            return 0.0
        return len(matches) / max(len(source_tokens), 1)

    def _similarity_score(self, normalized_source: str, field_name: str, rule: Any) -> float:
        candidates = [field_name, *getattr(rule, "aliases", ())]
        return max(
            SequenceMatcher(None, normalized_source, compact_field_name(candidate)).ratio()
            for candidate in candidates
        )

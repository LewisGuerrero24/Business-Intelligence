from __future__ import annotations

from typing import Any

from etl_service.domain.models import ImportSpec
from etl_service.etl.preclean.header_normalizer import compact_field_name


class SemanticFieldDisambiguator:
    def __init__(self) -> None:
        self.entity_rules = {
            "branches": {
                "name": ("sucursal", "sede", "nombre_sucursal", "nombre_sede", "local"),
                "code": ("codigo_sucursal", "sucursal_codigo", "codigo_sede", "codigo_local"),
                "address": ("direccion_sucursal", "direccion_sede", "direccion_completa"),
                "phone": ("telefono_sucursal", "telefono_sede", "telefono_contacto"),
            },
            "categories": {
                "name": ("categoria", "nombre_categoria", "linea", "familia"),
                "parent_category_id": (
                    "categoria_padre",
                    "categoria_padre_nombre",
                    "categoria_padre_codigo",
                    "linea_padre",
                    "familia_padre",
                ),
            },
            "customers": {
                "name": ("cliente", "nombre_cliente", "razon_social_cliente"),
                "tax_id": ("cliente_nit", "nit_cliente", "documento_cliente"),
                "erp_customer_code": ("codigo_cliente", "cliente_codigo", "codigo_cliente_erp"),
                "contact_name": ("contacto_cliente", "nombre_contacto_cliente"),
                "contact_email": ("correo_cliente", "email_cliente", "mail_cliente"),
                "contact_phone": ("telefono_cliente", "tel_cliente"),
                "contact_mobile": ("celular_cliente", "movil_cliente"),
            },
            "products": {
                "barcode": (
                    "barcode",
                    "codigo_barras",
                    "cod_barras",
                    "ean",
                    "ean13",
                    "upc",
                ),
                "sku": (
                    "sku",
                    "codigo_producto",
                    "cod_producto",
                    "producto_codigo",
                    "referencia",
                    "codigo_item",
                    "item_code",
                ),
                "category_id": (
                    "categoria",
                    "categoria_nombre",
                    "nombre_categoria",
                    "codigo_categoria",
                    "categoria_codigo",
                    "linea",
                    "familia",
                ),
                "supplier_id_fk": (
                    "proveedor",
                    "proveedor_nombre",
                    "nombre_proveedor",
                    "proveedor_nit",
                    "nit_proveedor",
                    "codigo_proveedor",
                ),
            },
            "suppliers": {
                "name": ("proveedor", "nombre_proveedor", "razon_social_proveedor"),
                "erp_supplier_code": (
                    "codigo_proveedor",
                    "proveedor_codigo",
                    "codigo_proveedor_erp",
                    "proveedor_nit",
                    "nit_proveedor",
                ),
            },
            "purchases": {
                "supplier_id": (
                    "proveedor",
                    "proveedor_nombre",
                    "nombre_proveedor",
                    "proveedor_nit",
                    "nit_proveedor",
                    "codigo_proveedor",
                ),
                "branch_id": (
                    "sucursal",
                    "sucursal_nombre",
                    "nombre_sucursal",
                    "sucursal_codigo",
                    "codigo_sucursal",
                    "sede",
                    "codigo_sede",
                ),
                "purchase_order_number": (
                    "orden",
                    "orden_compra",
                    "numero_orden",
                    "numero_oc",
                    "oc",
                ),
                "invoice_number": ("factura", "numero_factura", "nro_factura"),
            },
            "sales": {
                "customer_id": (
                    "cliente",
                    "cliente_nombre",
                    "nombre_cliente",
                    "cliente_nit",
                    "nit_cliente",
                    "codigo_cliente",
                ),
                "branch_id": (
                    "sucursal",
                    "sucursal_nombre",
                    "nombre_sucursal",
                    "sucursal_codigo",
                    "codigo_sucursal",
                    "sede",
                    "codigo_sede",
                ),
                "invoice_number": ("factura", "numero_factura", "nro_factura"),
            },
            "purchase_details": {
                "purchase_id": ("compra", "orden_compra", "numero_orden", "factura_compra"),
                "product_id": (
                    "producto",
                    "producto_nombre",
                    "nombre_producto",
                    "producto_codigo",
                    "codigo_producto",
                    "sku",
                    "referencia",
                    "barcode",
                ),
            },
            "purchases_details": {
                "purchase_id": ("compra", "orden_compra", "numero_orden", "factura_compra"),
                "product_id": (
                    "producto",
                    "producto_nombre",
                    "nombre_producto",
                    "producto_codigo",
                    "codigo_producto",
                    "sku",
                    "referencia",
                    "barcode",
                ),
            },
            "sales_details": {
                "sales_id": ("venta", "factura", "numero_factura", "factura_venta"),
                "product_id": (
                    "producto",
                    "producto_nombre",
                    "nombre_producto",
                    "producto_codigo",
                    "codigo_producto",
                    "sku",
                    "referencia",
                    "barcode",
                ),
            },
            "inventory_movement": {
                "inventory_id_fk": ("inventario", "inventory", "inventario_codigo"),
                "product_id_fk": (
                    "producto",
                    "producto_nombre",
                    "nombre_producto",
                    "producto_codigo",
                    "codigo_producto",
                    "sku",
                    "referencia",
                    "barcode",
                ),
            },
        }

    def target_for(
        self,
        *,
        source_field: str,
        spec: ImportSpec,
        field_rules: dict[str, Any],
    ) -> tuple[str | None, float]:
        normalized_source = compact_field_name(source_field)
        entity_rules = self.entity_rules.get(spec.import_type, {})

        for target_field, aliases in entity_rules.items():
            if target_field not in spec.columns or target_field not in field_rules:
                continue
            normalized_aliases = {compact_field_name(alias) for alias in aliases}
            if normalized_source in normalized_aliases:
                return target_field, 0.96

        source_tokens = set(normalized_source.split("_"))
        for target_field, aliases in entity_rules.items():
            if target_field not in spec.columns or target_field not in field_rules:
                continue
            for alias in aliases:
                alias_tokens = set(compact_field_name(alias).split("_"))
                if alias_tokens and alias_tokens.issubset(source_tokens):
                    return target_field, 0.88

        return None, 0.0

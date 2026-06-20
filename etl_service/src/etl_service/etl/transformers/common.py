import re
from typing import Any

from etl_service.domain.models import ImportSpec


FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "name": ("name", "nombre", "razon_social", "cliente", "proveedor", "sucursal", "categoria", "producto"),
    "code": ("code", "codigo", "cod", "codigo_sucursal"),
    "address": ("address", "direccion"),
    "city": ("city", "ciudad"),
    "phone": ("phone", "telefono", "tel"),
    "company_id": ("company_id", "empresa_id", "id_empresa"),
    "company_id_fk": ("company_id_fk", "company_id", "empresa_id", "id_empresa"),
    "category_id": ("category_id", "categoria_id", "id_categoria"),
    "parent_category_id": ("parent_category_id", "categoria_padre_id"),
    "supplier_id": ("supplier_id", "proveedor_id", "id_proveedor"),
    "supplier_id_fk": ("supplier_id_fk", "supplier_id", "proveedor_id"),
    "product_id": ("product_id", "producto_id", "id_producto"),
    "product_id_fk": ("product_id_fk", "product_id", "producto_id"),
    "branch_id": ("branch_id", "sucursal_id", "id_sucursal"),
    "branch_id_fk": ("branch_id_fk", "branch_id", "sucursal_id"),
    "customer_id": ("customer_id", "cliente_id", "id_cliente"),
    "erp_supplier_code": ("erp_supplier_code", "codigo_proveedor_erp", "codigo_erp"),
    "erp_customer_code": ("erp_customer_code", "codigo_cliente_erp", "codigo_erp"),
    "erp_product_code": ("erp_product_code", "codigo_producto_erp", "codigo_erp"),
    "tax_id": ("tax_id", "nit", "rut", "rfc", "identificacion"),
    "sku": ("sku", "codigo_producto", "referencia"),
    "barcode": ("barcode", "codigo_barras", "ean"),
    "description": ("description", "descripcion"),
    "unit_of_measure": ("unit_of_measure", "unidad_medida", "unidad"),
    "cost_price": ("cost_price", "costo", "costo_promedio"),
    "sale_price": ("sale_price", "precio_venta", "precio"),
    "min_stock": ("min_stock", "stock_minimo"),
    "max_stock": ("max_stock", "stock_maximo"),
    "reorder_point": ("reorder_point", "punto_reorden"),
    "category_abc": ("category_ABC", "category_abc", "abc", "categoria_abc"),
    "is_active": ("is_active", "activo", "estado"),
    "is_taxable": ("is_taxable", "gravado", "maneja_impuesto"),
    "tax_rate": ("tax_rate", "iva", "impuesto", "tasa_impuesto"),
    "customer_type": ("customer_type", "tipo_cliente"),
    "contact_name": ("contact_name", "nombre_contacto"),
    "contact_email": ("contact_email", "email", "correo"),
    "contact_phone": ("contact_phone", "telefono_contacto"),
    "contact_mobile": ("contact_mobile", "celular", "movil"),
    "billing_address": ("billing_address", "direccion_facturacion"),
    "notes": ("notes", "notas", "observaciones"),
    "purchase_id": ("purchase_id", "compra_id", "id_compra"),
    "purchases_id": ("purchases_id", "compra_id", "id_compra"),
    "purchase_order_number": ("purchase_order_number", "orden_compra", "numero_orden"),
    "purchase_date": ("purchase_date", "fecha_compra"),
    "expected_delivery_date": ("expected_delivery_date", "fecha_entrega_esperada"),
    "received_date": ("received_date", "fecha_recibido"),
    "invoice_number": ("invoice_number", "factura", "numero_factura"),
    "sale_date": ("sale_date", "fecha_venta"),
    "status": ("status", "estado"),
    "payment_method": ("payment_method", "metodo_pago", "forma_pago"),
    "payment_status": ("payment_status", "estado_pago"),
    "payment_due_date": ("payment_due_date", "fecha_vencimiento_pago"),
    "subtotal": ("subtotal", "sub_total"),
    "tax_amount": ("tax_amount", "valor_impuesto", "iva_valor"),
    "discount_amount": ("discount_amount", "descuento"),
    "discount_percent": ("discount_percent", "porcentaje_descuento"),
    "total_amount": ("total_amount", "total"),
    "total": ("total", "valor_total"),
    "quantity": ("quantity", "cantidad"),
    "quantity_ordered": ("quantity_ordered", "cantidad_ordenada"),
    "quantity_received": ("quantity_received", "cantidad_recibida"),
    "unit_cost": ("unit_cost", "costo_unitario"),
    "unit_price": ("unit_price", "precio_unitario"),
    "cost_total": ("cost_total", "costo_total"),
    "profit_amount": ("profit_amount", "utilidad"),
    "profit_margin_percent": ("profit_margin_percent", "margen_utilidad"),
    "inventory_id_fk": ("inventory_id_fk", "inventory_id", "inventario_id"),
    "movement_type": ("movement_type", "tipo_movimiento"),
    "reference_type": ("reference_type", "tipo_referencia"),
    "previous_stock": ("previous_stock", "stock_anterior"),
    "new_stock": ("new_stock", "stock_nuevo"),
    "initial_count": ("initial_count", "conteo_inicial"),
    "final_count": ("final_count", "conteo_final"),
    "is_closed": ("is_closed", "cerrado"),
    "closed_at": ("closed_at", "fecha_cierre"),
    "closed_by": ("closed_by", "cerrado_por"),
    "start_date": ("start_date", "fecha_inicio"),
    "end_date": ("end_date", "fecha_fin"),
    "created_by": ("created_by", "creado_por"),
}

BOOL_TRUE = {"true", "1", "si", "s", "yes", "y", "activo", "active"}
BOOL_FALSE = {"false", "0", "no", "n", "inactivo", "inactive"}


def transform_raw_row(raw_data: dict[str, Any], spec: ImportSpec, company_id: str | None) -> dict[str, Any]:
    normalized = {_normalize_key(key): value for key, value in raw_data.items()}
    clean: dict[str, Any] = dict(spec.default_values)

    for column in spec.columns:
        value = _find_value(column, normalized)
        if value is not None:
            clean[column] = _clean_value(column, value, spec)

    if spec.force_company_id and company_id:
        clean["company_id"] = company_id

    if spec.dw_table == "inventory" and company_id:
        clean.setdefault("company_id_fk", company_id)

    return {key: value for key, value in clean.items() if value is not None}


def _find_value(column: str, normalized: dict[str, Any]) -> Any:
    aliases = FIELD_ALIASES.get(column, (column,))
    for alias in aliases:
        key = _normalize_key(alias)
        if key in normalized:
            return normalized[key]
    return None


def _clean_value(column: str, value: Any, spec: ImportSpec) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None

    if column in {"is_active", "is_taxable", "is_primary", "is_closed"}:
        return _to_bool(value)

    if column in spec.enum_fields and isinstance(value, str):
        return value.strip().upper()

    return value


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in BOOL_TRUE:
        return True
    if text in BOOL_FALSE:
        return False
    return None


def _normalize_key(value: str) -> str:
    key = value.strip().replace("-", "_").replace(" ", "_")
    key = re.sub(r"__+", "_", key)
    return key.lower()

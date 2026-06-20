from etl_service.etl.processors.base import BaseProcessor, FieldRule, RelationRule


class PurchaseDetailProcessor(BaseProcessor):
    import_type = "purchase_details"
    field_rules = {
        "purchase_detail_id": FieldRule(("purchase_detail_id", "detalle_compra_id"), "uuid"),
        "purchase_id": FieldRule(
            ("purchase_id", "purchases_id", "compra_id"),
            "uuid",
            required=True,
        ),
        "product_id": FieldRule(
            ("product_id", "producto_id", "id_producto"),
            "uuid",
            required=True,
        ),
        "quantity_ordered": FieldRule(
            ("quantity_ordered", "cantidad_ordenada"),
            "numeric",
            default=0,
        ),
        "quantity_received": FieldRule(
            ("quantity_received", "cantidad_recibida"),
            "numeric",
            default=0,
        ),
        "unit_price": FieldRule(("unit_price", "precio_unitario"), "numeric", default=0),
        "discount_percent": FieldRule(
            ("discount_percent", "porcentaje_descuento"),
            "numeric",
            default=0,
        ),
        "subtotal": FieldRule(("subtotal", "sub_total"), "numeric", default=0),
        "tax_amount": FieldRule(
            ("tax_amount", "valor_impuesto", "iva_valor"),
            "numeric",
            default=0,
        ),
        "total": FieldRule(("total", "valor_total"), "numeric", default=0),
        "notes": FieldRule(("notes", "notas", "observaciones")),
    }
    relation_rules = (
        RelationRule("purchase_id", "purchases", "purchases_id"),
        RelationRule("product_id", "products", "product_id"),
    )

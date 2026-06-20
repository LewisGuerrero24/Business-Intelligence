from etl_service.etl.processors.base import BaseProcessor, FieldRule, RelationRule


class SaleDetailProcessor(BaseProcessor):
    import_type = "sales_details"
    field_rules = {
        "sales_details_id": FieldRule(("sales_details_id", "sale_detail_id"), "uuid"),
        "sales_id": FieldRule(("sales_id", "venta_id"), "uuid", required=True),
        "product_id": FieldRule(
            ("product_id", "producto_id", "id_producto"),
            "uuid",
            required=True,
        ),
        "quantity": FieldRule(("quantity", "cantidad"), "numeric", default=1),
        "unit_cost": FieldRule(("unit_cost", "costo_unitario"), "numeric", default=0),
        "unit_price": FieldRule(("unit_price", "precio_unitario"), "numeric", default=0),
        "discount_percent": FieldRule(
            ("discount_percent", "porcentaje_descuento"),
            "numeric",
            default=0,
        ),
        "subtotal": FieldRule(("subtotal", "sub_total"), "numeric", default=0),
        "cost_total": FieldRule(("cost_total", "costo_total"), "numeric", default=0),
        "profit_amount": FieldRule(("profit_amount", "utilidad"), "numeric", default=0),
        "profit_margin_percent": FieldRule(
            ("profit_margin_percent", "margen_utilidad"),
            "numeric",
            default=0,
        ),
        "tax_amount": FieldRule(
            ("tax_amount", "valor_impuesto", "iva_valor"),
            "numeric",
            default=0,
        ),
        "total": FieldRule(("total", "valor_total"), "numeric", default=0),
    }
    relation_rules = (
        RelationRule("sales_id", "sales", "sales_id"),
        RelationRule("product_id", "products", "product_id"),
    )

from etl_service.etl.processors.base import BaseProcessor, FieldRule, RelationRule


class SaleProcessor(BaseProcessor):
    import_type = "sales"
    field_rules = {
        "sales_id": FieldRule(("sales_id", "venta_id"), "uuid"),
        "company_id": FieldRule(("company_id", "empresa_id", "id_empresa"), "uuid", required=True),
        "customer_id": FieldRule(
            ("customer_id", "cliente_id", "id_cliente"),
            "uuid",
            required=True,
        ),
        "branch_id": FieldRule(("branch_id", "sucursal_id", "id_sucursal"), "uuid", required=True),
        "sale_date": FieldRule(("sale_date", "fecha_venta"), "date", required=True),
        "invoice_number": FieldRule(("invoice_number", "factura", "numero_factura"), required=True),
        "status": FieldRule(
            ("status", "estado"),
            "enum",
            enum_values=("DRAFT", "CONFIRMED", "CANCELLED"),
            default="DRAFT",
        ),
        "payment_method": FieldRule(
            ("payment_method", "metodo_pago", "forma_pago"),
            "enum",
            required=True,
            enum_values=("CASH", "CARD", "TRANSFER", "CREDIT"),
        ),
        "payment_status": FieldRule(
            ("payment_status", "estado_pago"),
            "enum",
            enum_values=("PENDING", "PARTIAL", "PAID"),
            default="PENDING",
        ),
        "subtotal": FieldRule(("subtotal", "sub_total"), "numeric", default=0),
        "tax_amount": FieldRule(
            ("tax_amount", "valor_impuesto", "iva_valor"),
            "numeric",
            default=0,
        ),
        "discount_amount": FieldRule(("discount_amount", "descuento"), "numeric", default=0),
        "total_amount": FieldRule(("total_amount", "total"), "numeric", default=0),
        "notes": FieldRule(("notes", "notas", "observaciones")),
    }
    relation_rules = (
        RelationRule("company_id", "companies", "company_id"),
        RelationRule("customer_id", "customers", "customer_id"),
        RelationRule("branch_id", "branches", "branch_id"),
    )

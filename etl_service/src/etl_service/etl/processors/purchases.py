from etl_service.etl.processors.base import BaseProcessor, FieldRule, RelationRule


class PurchaseProcessor(BaseProcessor):
    import_type = "purchases"
    field_rules = {
        "purchases_id": FieldRule(("purchases_id", "purchase_id", "compra_id"), "uuid"),
        "company_id": FieldRule(("company_id", "empresa_id", "id_empresa"), "uuid", required=True),
        "supplier_id": FieldRule(
            ("supplier_id", "proveedor_id", "id_proveedor"),
            "uuid",
            required=True,
        ),
        "branch_id": FieldRule(("branch_id", "sucursal_id", "id_sucursal"), "uuid", required=True),
        "purchase_order_number": FieldRule(
            ("purchase_order_number", "orden_compra", "numero_orden"),
            required=True,
        ),
        "purchase_date": FieldRule(("purchase_date", "fecha_compra"), "date", required=True),
        "expected_delivery_date": FieldRule(
            ("expected_delivery_date", "fecha_entrega_esperada"),
            "date",
        ),
        "received_date": FieldRule(("received_date", "fecha_recibido"), "date"),
        "invoice_number": FieldRule(("invoice_number", "factura", "numero_factura")),
        "status": FieldRule(
            ("status", "estado"),
            "enum",
            enum_values=("DRAFT", "CONFIRMED", "RECEIVED", "CANCELLED"),
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
        "payment_due_date": FieldRule(("payment_due_date", "fecha_vencimiento_pago"), "date"),
        "subtotal": FieldRule(("subtotal", "sub_total"), "numeric", default=0),
        "tax_amount": FieldRule(
            ("tax_amount", "valor_impuesto", "iva_valor"),
            "numeric",
            default=0,
        ),
        "total_amount": FieldRule(("total_amount", "total"), "numeric", default=0),
        "notes": FieldRule(("notes", "notas", "observaciones")),
    }
    relation_rules = (
        RelationRule("company_id", "companies", "company_id"),
        RelationRule("supplier_id", "suppliers", "supplier_id"),
        RelationRule("branch_id", "branches", "branch_id"),
    )

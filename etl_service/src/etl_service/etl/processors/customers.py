from etl_service.etl.processors.base import BaseProcessor, FieldRule, RelationRule


class CustomerProcessor(BaseProcessor):
    import_type = "customers"
    field_rules = {
        "customer_id": FieldRule(("customer_id", "cliente_id", "id_cliente"), "uuid"),
        "company_id": FieldRule(("company_id", "empresa_id", "id_empresa"), "uuid", required=True),
        "customer_type": FieldRule(
            ("customer_type", "tipo_cliente"),
            "enum",
            required=True,
            enum_values=("INDIVIDUAL", "BUSINESS"),
        ),
        "erp_customer_code": FieldRule(("erp_customer_code", "codigo_cliente_erp", "codigo_erp")),
        "tax_id": FieldRule(("tax_id", "nit", "rut", "rfc", "identificacion")),
        "name": FieldRule(("name", "nombre", "cliente", "customer_name"), required=True),
        "contact_name": FieldRule(("contact_name", "nombre_contacto")),
        "contact_email": FieldRule(("contact_email", "email", "correo")),
        "contact_phone": FieldRule(("contact_phone", "telefono_contacto")),
        "contact_mobile": FieldRule(("contact_mobile", "celular", "movil")),
        "billing_address": FieldRule(("billing_address", "direccion_facturacion")),
        "is_active": FieldRule(("is_active", "activo", "estado"), "boolean", default=True),
        "notes": FieldRule(("notes", "notas", "observaciones")),
    }
    relation_rules = (RelationRule("company_id", "companies", "company_id"),)

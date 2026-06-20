from etl_service.etl.processors.base import BaseProcessor, FieldRule, RelationRule


class SupplierProcessor(BaseProcessor):
    import_type = "suppliers"
    field_rules = {
        "supplier_id": FieldRule(("supplier_id", "proveedor_id", "id_proveedor"), "uuid"),
        "company_id": FieldRule(("company_id", "empresa_id", "id_empresa"), "uuid", required=True),
        "erp_supplier_code": FieldRule(
            ("erp_supplier_code", "codigo_proveedor_erp", "codigo_erp", "supplier_code")
        ),
        "name": FieldRule(("name", "nombre", "proveedor", "supplier_name"), required=True),
        "is_active": FieldRule(("is_active", "activo", "estado"), "boolean", default=True),
    }
    relation_rules = (RelationRule("company_id", "companies", "company_id"),)

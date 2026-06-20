from etl_service.etl.processors.base import BaseProcessor, FieldRule, RelationRule


class CategoryProcessor(BaseProcessor):
    import_type = "categories"
    field_rules = {
        "category_id": FieldRule(("category_id", "categoria_id", "id_categoria"), "uuid"),
        "company_id": FieldRule(("company_id", "empresa_id", "id_empresa"), "uuid", required=True),
        "parent_category_id": FieldRule(("parent_category_id", "categoria_padre_id"), "uuid"),
        "name": FieldRule(("name", "nombre", "categoria", "category_name"), required=True),
        "description": FieldRule(("description", "descripcion")),
        "display_order": FieldRule(("display_order", "orden", "orden_visual"), "numeric"),
        "is_active": FieldRule(("is_active", "activo", "estado"), "boolean", default=True),
    }
    relation_rules = (
        RelationRule("company_id", "companies", "company_id"),
        RelationRule("parent_category_id", "categories", "category_id"),
    )

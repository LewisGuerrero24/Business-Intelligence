from etl_service.etl.processors.base import BaseProcessor, FieldRule, RelationRule


class ProductProcessor(BaseProcessor):
    import_type = "products"
    field_rules = {
        "product_id": FieldRule(("product_id", "producto_id", "id_producto"), "uuid"),
        "company_id": FieldRule(("company_id", "empresa_id", "id_empresa"), "uuid", required=True),
        "category_id": FieldRule(
            ("category_id", "categoria_id", "id_categoria"),
            "uuid",
            required=True,
        ),
        "supplier_id_fk": FieldRule(("supplier_id_fk", "supplier_id", "proveedor_id"), "uuid"),
        "erp_product_code": FieldRule(("erp_product_code", "codigo_erp", "product_code")),
        "sku": FieldRule(
            ("sku", "SKU", "codigo", "codigo_producto", "product_code", "erp_product_code"),
            required=True,
        ),
        "barcode": FieldRule(("barcode", "codigo_barras", "ean")),
        "name": FieldRule(
            ("name", "nombre", "product_name", "descripcion_producto"),
            required=True,
        ),
        "description": FieldRule(("description", "descripcion")),
        "unit_of_measure": FieldRule(
            ("unit_of_measure", "unidad_medida", "unidad"),
            "enum",
            required=True,
            enum_values=("UNIT", "KG", "L", "M", "BOX", "PACK"),
        ),
        "cost_price": FieldRule(
            ("cost_price", "costo", "precio_costo", "unit_cost"),
            "numeric",
            default=0,
        ),
        "sale_price": FieldRule(
            ("sale_price", "precio_venta", "price", "valor_venta"),
            "numeric",
            default=0,
        ),
        "min_stock": FieldRule(("min_stock", "stock_minimo"), "numeric", default=0),
        "max_stock": FieldRule(("max_stock", "stock_maximo"), "numeric", default=0),
        "reorder_point": FieldRule(("reorder_point", "punto_reorden"), "numeric"),
        "is_active": FieldRule(("is_active", "activo", "estado"), "boolean", default=True),
        "category_abc": FieldRule(("category_abc", "category_ABC", "abc", "categoria_abc")),
        "is_taxable": FieldRule(
            ("is_taxable", "gravado", "maneja_impuesto"),
            "boolean",
            default=True,
        ),
        "tax_rate": FieldRule(
            ("tax_rate", "iva", "impuesto", "tasa_impuesto"),
            "numeric",
            default=0,
        ),
    }
    relation_rules = (
        RelationRule("company_id", "companies", "company_id"),
        RelationRule("category_id", "categories", "category_id"),
        RelationRule("supplier_id_fk", "suppliers", "supplier_id"),
    )

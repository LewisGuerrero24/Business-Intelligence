from etl_service.etl.processors.base import BaseProcessor, FieldRule, RelationRule


class InventoryMovementProcessor(BaseProcessor):
    import_type = "inventory_movement"
    field_rules = {
        "movement_id": FieldRule(("movement_id", "movimiento_id"), "uuid"),
        "inventory_id_fk": FieldRule(
            ("inventory_id_fk", "inventory_id", "inventario_id"),
            "uuid",
            required=True,
        ),
        "product_id_fk": FieldRule(
            ("product_id_fk", "product_id", "producto_id"),
            "uuid",
            required=True,
        ),
        "movement_type": FieldRule(
            ("movement_type", "tipo_movimiento"),
            "enum",
            required=True,
            enum_values=("IN", "OUT", "ABJUSTMENT", "T"),
        ),
        "reference_type": FieldRule(
            ("reference_type", "tipo_referencia"),
            "enum",
            required=True,
            enum_values=("SALE", "PURCHASE", "ABJUSTMENT"),
        ),
        "quantity": FieldRule(("quantity", "cantidad"), "numeric", required=True),
        "unit_cost": FieldRule(("unit_cost", "costo_unitario"), "numeric", required=True),
        "previous_stock": FieldRule(("previous_stock", "stock_anterior"), "numeric", required=True),
        "new_stock": FieldRule(("new_stock", "stock_nuevo"), "numeric", required=True),
        "notes": FieldRule(("notes", "notas", "observaciones")),
        "created_by": FieldRule(("created_by", "creado_por"), "uuid", required=True),
    }
    relation_rules = (
        RelationRule("inventory_id_fk", "inventory", "inventory_id"),
        RelationRule("product_id_fk", "products", "product_id"),
    )

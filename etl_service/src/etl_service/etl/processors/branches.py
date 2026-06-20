from etl_service.etl.processors.base import BaseProcessor, FieldRule, RelationRule


class BranchProcessor(BaseProcessor):
    import_type = "branches"
    field_rules = {
        "branch_id": FieldRule(("branch_id", "sucursal_id", "id_sucursal"), "uuid"),
        "company_id": FieldRule(("company_id", "empresa_id", "id_empresa"), "uuid", required=True),
        "name": FieldRule(
            (
                "name",
                "nombre",
                "sucursal",
                "branch_name",
                "nombre_comercial_sede",
                "nombre sede",
                "sede",
            ),
            required=True,
        ),
        "code": FieldRule(
            (
                "code",
                "codigo",
                "cod",
                "codigo_sucursal",
                "branch_code",
                "codigo_local",
                "codigo sede",
            )
        ),
        "address": FieldRule(
            (
                "address",
                "direccion",
                "direccion_sucursal",
                "direccion_completa",
                "direccion sede",
            )
        ),
        "city": FieldRule(("city", "ciudad", "municipio")),
        "phone": FieldRule(("phone", "telefono", "tel", "telefono_contacto")),
        "is_active": FieldRule(
            (
                "is_active",
                "activo",
                "estado",
                "estado_operativo",
                "estatus",
            ),
            "boolean",
            default=True,
        ),
    }
    relation_rules = (RelationRule("company_id", "companies", "company_id"),)

from typing import Any
from uuid import UUID

from etl_service.domain.enums import ErrorType, Severity
from etl_service.domain.models import ImportSpec, ValidationError


UUID_FIELDS = {
    "company_id",
    "company_id_fk",
    "branch_id",
    "branch_id_fk",
    "category_id",
    "parent_category_id",
    "customer_id",
    "supplier_id",
    "supplier_id_fk",
    "product_id",
    "product_id_fk",
    "purchase_id",
    "purchases_id",
    "sales_id",
    "inventory_id_fk",
    "closed_by",
    "created_by",
}


def validate_clean_row(
    clean_data: dict[str, Any],
    spec: ImportSpec,
    row_number: int,
) -> list[ValidationError]:
    errors: list[ValidationError] = []

    for field in spec.required_fields:
        if clean_data.get(field) in (None, ""):
            errors.append(
                ValidationError(
                    row_number=row_number,
                    error_type=ErrorType.REQUIRED_FIELD,
                    severity=Severity.ERROR,
                    field_name=field,
                    field_value=None,
                    expected_format="required",
                    error_message=f"Required field {field} is missing.",
                    suggested_fix=f"Provide a value for {field}.",
                )
            )

    for field, accepted_values in spec.enum_fields.items():
        value = clean_data.get(field)
        if value is not None and value not in accepted_values:
            errors.append(
                ValidationError(
                    row_number=row_number,
                    error_type=ErrorType.VALIDATION,
                    severity=Severity.ERROR,
                    field_name=field,
                    field_value=str(value),
                    expected_format=", ".join(accepted_values),
                    error_message=f"Invalid value for {field}.",
                    suggested_fix=f"Use one of: {', '.join(accepted_values)}.",
                )
            )

    for field in UUID_FIELDS.intersection(clean_data):
        value = clean_data.get(field)
        if value not in (None, "") and not _is_uuid(value):
            errors.append(
                ValidationError(
                    row_number=row_number,
                    error_type=ErrorType.DATA_TYPE,
                    severity=Severity.ERROR,
                    field_name=field,
                    field_value=str(value),
                    expected_format="UUID",
                    error_message=f"Field {field} must be a valid UUID.",
                    suggested_fix="Use the UUID from the related DW table.",
                )
            )

    return errors


def _is_uuid(value: Any) -> bool:
    try:
        UUID(str(value))
    except (TypeError, ValueError):
        return False
    return True


from typing import Any

from etl_service.domain.enums import ErrorType
from etl_service.domain.models import ValidationError
from etl_service.etl.utils.errors import add_error


def required(
    errors: list[ValidationError],
    *,
    row_number: int,
    value: Any,
    field_name: str,
) -> None:
    if value in (None, ""):
        add_error(
            errors,
            row_number=row_number,
            field_name=field_name,
            error_type=ErrorType.REQUIRED_FIELD,
            message=f"Required field {field_name} is missing.",
            expected_format="required",
            suggested_fix=f"Provide a value for {field_name}.",
        )

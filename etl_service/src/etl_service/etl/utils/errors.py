from typing import Any

from etl_service.domain.enums import ErrorType, Severity
from etl_service.domain.models import ValidationError


def add_error(
    errors: list[ValidationError],
    *,
    row_number: int,
    field_name: str | None,
    error_type: ErrorType | str,
    message: str,
    field_value: Any = None,
    expected_format: str | None = None,
    suggested_fix: str | None = None,
) -> None:
    errors.append(
        ValidationError(
            row_number=row_number,
            error_type=str(error_type.value if isinstance(error_type, ErrorType) else error_type),
            severity=Severity.ERROR.value,
            field_name=field_name,
            field_value=str(field_value) if field_value is not None else None,
            expected_format=expected_format,
            error_message=message,
            suggested_fix=suggested_fix,
        )
    )

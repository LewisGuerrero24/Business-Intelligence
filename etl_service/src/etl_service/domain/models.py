from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ImportSpec:
    import_type: str
    staging_table: str
    staging_pk: str
    dw_table: str
    dw_pk: str
    columns: tuple[str, ...]
    required_fields: tuple[str, ...] = ()
    lookup_groups: tuple[tuple[str, ...], ...] = ()
    enum_fields: dict[str, tuple[str, ...]] = field(default_factory=dict)
    default_values: dict[str, Any] = field(default_factory=dict)
    force_company_id: bool = True


@dataclass(frozen=True)
class ExtractedRow:
    row_number: int
    raw_data: dict[str, Any]
    chunk_number: int | None = None


@dataclass(frozen=True)
class ValidationError:
    row_number: int
    error_type: str
    severity: str
    field_name: str | None
    field_value: str | None
    expected_format: str | None
    error_message: str
    suggested_fix: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "row_number": self.row_number,
            "error_type": self.error_type,
            "severity": self.severity,
            "field_name": self.field_name,
            "field_value": self.field_value,
            "expected_format": self.expected_format,
            "error_message": self.error_message,
            "suggested_fix": self.suggested_fix,
        }


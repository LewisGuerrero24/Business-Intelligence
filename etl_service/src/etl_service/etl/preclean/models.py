from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceField:
    source_field: str
    normalized_source_field: str
    value: Any


@dataclass(frozen=True)
class FieldCandidate:
    target_field: str
    source_field: str
    normalized_source_field: str
    source_value: Any
    rule: str
    confidence: float
    warning: str | None = None


@dataclass(frozen=True)
class FieldTrace:
    target_field: str
    source_field: str
    source_value: Any
    final_value: Any
    rule: str
    confidence: float
    warning: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_field": self.target_field,
            "source_field": self.source_field,
            "source_value": self.source_value,
            "final_value": self.final_value,
            "rule": self.rule,
            "confidence": self.confidence,
            "warning": self.warning,
        }


@dataclass(frozen=True)
class InterpretationWarning:
    field_name: str | None
    warning_type: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "warning_type": self.warning_type,
            "message": self.message,
        }


@dataclass(frozen=True)
class InterpretedRow:
    clean_candidate: dict[str, Any]
    mapping_trace: list[FieldTrace] = field(default_factory=list)
    unmapped_fields: dict[str, Any] = field(default_factory=dict)
    warnings: list[InterpretationWarning] = field(default_factory=list)
    confidence: dict[str, float] = field(default_factory=dict)

    def metadata(self) -> dict[str, Any]:
        return {
            "mapping_trace": [trace.as_dict() for trace in self.mapping_trace],
            "unmapped_fields": self.unmapped_fields,
            "warnings": [warning.as_dict() for warning in self.warnings],
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class MappingResult:
    mapped_data: dict[str, Any]
    mapping_trace: list[FieldTrace]
    unmapped_fields: dict[str, Any]
    warnings: list[InterpretationWarning]
    confidence: dict[str, float]


@dataclass(frozen=True)
class RelationshipResult:
    resolved_data: dict[str, Any]
    mapping_trace: list[FieldTrace] = field(default_factory=list)
    warnings: list[InterpretationWarning] = field(default_factory=list)
    confidence: dict[str, float] = field(default_factory=dict)

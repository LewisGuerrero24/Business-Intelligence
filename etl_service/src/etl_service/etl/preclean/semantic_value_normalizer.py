from __future__ import annotations

from typing import Any

from etl_service.etl.preclean.business_vocabulary import BusinessVocabulary
from etl_service.etl.preclean.models import FieldTrace, InterpretationWarning


class SemanticValueNormalizer:
    def __init__(self) -> None:
        self.vocabulary = BusinessVocabulary()

    def normalize(
        self,
        *,
        import_type: str,
        data: dict[str, Any],
        field_rules: dict[str, Any],
        confidence: dict[str, float],
    ) -> tuple[dict[str, Any], list[FieldTrace], list[InterpretationWarning], dict[str, float]]:
        normalized = dict(data)
        traces: list[FieldTrace] = []
        warnings: list[InterpretationWarning] = []
        semantic_confidence: dict[str, float] = {}

        for field_name, rule in field_rules.items():
            if field_name not in normalized:
                continue
            if getattr(rule, "field_type", None) != "enum":
                continue

            value = normalized.get(field_name)
            if value in (None, ""):
                continue

            resolved = self.vocabulary.enum_value(
                field_name,
                value,
                getattr(rule, "enum_values", ()),
            )
            if resolved is None:
                warnings.append(
                    InterpretationWarning(
                        field_name=field_name,
                        warning_type="SEMANTIC_ENUM_NOT_RESOLVED",
                        message=(
                            f"Value {value!r} for {field_name} could not be translated "
                            f"to an allowed {import_type} enum."
                        ),
                    )
                )
                continue

            if resolved == value:
                continue

            normalized[field_name] = resolved
            semantic_confidence[field_name] = max(confidence.get(field_name, 0.0), 0.97)
            traces.append(
                FieldTrace(
                    target_field=field_name,
                    source_field=field_name,
                    source_value=value,
                    final_value=resolved,
                    rule="semantic_enum_normalized",
                    confidence=0.97,
                )
            )

        return normalized, traces, warnings, semantic_confidence

from __future__ import annotations

from typing import Any

from etl_service.etl.preclean.models import FieldTrace, InterpretationWarning


class RowConfidenceEvaluator:
    def evaluate(
        self,
        *,
        clean_candidate: dict[str, Any],
        field_rules: dict[str, Any],
        confidence: dict[str, float],
    ) -> tuple[list[FieldTrace], list[InterpretationWarning], dict[str, float]]:
        required_fields = [
            field_name
            for field_name, rule in field_rules.items()
            if getattr(rule, "required", False)
        ]
        if not confidence and not required_fields:
            return [], [], {}

        relevant_scores = [
            confidence[field_name]
            for field_name in confidence
            if field_name in clean_candidate
        ]
        required_scores = [
            confidence.get(field_name, 0.0)
            for field_name in required_fields
            if clean_candidate.get(field_name) not in (None, "")
        ]
        scores = [*relevant_scores, *required_scores]
        row_confidence = round(sum(scores) / len(scores), 4) if scores else 0.0

        traces = [
            FieldTrace(
                target_field="_row",
                source_field="_row",
                source_value=None,
                final_value=row_confidence,
                rule="row_confidence_evaluated",
                confidence=row_confidence,
            )
        ]
        warnings: list[InterpretationWarning] = []
        if row_confidence and row_confidence < 0.76:
            warnings.append(
                InterpretationWarning(
                    field_name=None,
                    warning_type="ROW_CONFIDENCE_WARNING",
                    message=(
                        "Row was interpreted with low semantic confidence. "
                        "It will only be loaded if hard validations pass."
                    ),
                )
            )
            traces.append(
                FieldTrace(
                    target_field="_row",
                    source_field="_row",
                    source_value=None,
                    final_value=row_confidence,
                    rule="row_confidence_warning",
                    confidence=row_confidence,
                    warning="Low semantic confidence.",
                )
            )

        return traces, warnings, {"_row": row_confidence}

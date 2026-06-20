from __future__ import annotations

from typing import Any

from etl_service.domain.models import ImportSpec
from etl_service.etl.preclean.confidence import ConfidenceScorer
from etl_service.etl.preclean.contextual_mapper import ContextualFieldMapper
from etl_service.etl.preclean.header_normalizer import compact_field_name
from etl_service.etl.preclean.models import (
    FieldCandidate,
    FieldTrace,
    InterpretationWarning,
    MappingResult,
    SourceField,
)
from etl_service.etl.preclean.semantic_field_disambiguator import SemanticFieldDisambiguator
from etl_service.etl.preclean.type_profiler import TypeProfiler
from etl_service.repositories.control_repository import ControlRepository


class FieldMappingEngine:
    def __init__(self, control: ControlRepository) -> None:
        self.control = control
        self.contextual_mapper = ContextualFieldMapper()
        self.semantic_disambiguator = SemanticFieldDisambiguator()
        self.type_profiler = TypeProfiler()
        self.confidence_scorer = ConfidenceScorer()

    def map_fields(
        self,
        *,
        source_fields: list[SourceField],
        spec: ImportSpec,
        company_id: str | None,
        field_rules: dict[str, Any],
    ) -> MappingResult:
        learned_mappings = self._learned_mappings(
            company_id=company_id,
            import_type=spec.import_type,
        )
        alias_mappings = self._alias_mappings(field_rules)
        selected: dict[str, FieldCandidate] = {}
        unmapped_fields: dict[str, Any] = {}
        warnings: list[InterpretationWarning] = []

        for source in source_fields:
            candidate = self._candidate_for_source(
                source=source,
                spec=spec,
                field_rules=field_rules,
                learned_mappings=learned_mappings,
                alias_mappings=alias_mappings,
            )
            if candidate is None:
                unmapped_fields[source.source_field] = source.value
                continue

            if candidate.confidence < 0.7:
                unmapped_fields[source.source_field] = source.value
                warnings.append(
                    InterpretationWarning(
                        field_name=candidate.target_field,
                        warning_type="LOW_CONFIDENCE_MAPPING",
                        message=(
                            f"Column {source.source_field!r} looked like "
                            f"{candidate.target_field!r}, but confidence was too low."
                        ),
                    )
                )
                continue

            current = selected.get(candidate.target_field)
            if self._should_replace(current=current, candidate=candidate):
                selected[candidate.target_field] = candidate

            if (
                candidate.rule == "company_mapping"
                and company_id
                and candidate.confidence >= 0.9
            ):
                self.control.mark_field_mapping_used(
                    company_id=company_id,
                    import_type=spec.import_type,
                    normalized_source_field=source.normalized_source_field,
                    target_field=candidate.target_field,
                )

        mapped_data = {
            field_name: candidate.source_value
            for field_name, candidate in selected.items()
        }
        trace = [
            FieldTrace(
                target_field=field_name,
                source_field=candidate.source_field,
                source_value=candidate.source_value,
                final_value=candidate.source_value,
                rule=candidate.rule,
                confidence=candidate.confidence,
                warning=candidate.warning,
            )
            for field_name, candidate in selected.items()
        ]
        confidence = {
            field_name: candidate.confidence
            for field_name, candidate in selected.items()
        }
        warnings.extend(
            InterpretationWarning(
                field_name=candidate.target_field,
                warning_type="MEDIUM_CONFIDENCE_MAPPING",
                message=candidate.warning,
            )
            for candidate in selected.values()
            if candidate.warning
        )

        return MappingResult(
            mapped_data=mapped_data,
            mapping_trace=trace,
            unmapped_fields=unmapped_fields,
            warnings=warnings,
            confidence=confidence,
        )

    def _candidate_for_source(
        self,
        *,
        source: SourceField,
        spec: ImportSpec,
        field_rules: dict[str, Any],
        learned_mappings: dict[str, str],
        alias_mappings: dict[str, str],
    ) -> FieldCandidate | None:
        target_field = learned_mappings.get(source.normalized_source_field)
        rule = "company_mapping" if target_field else None
        semantic_confidence = 0.0

        if not target_field:
            target_field, semantic_confidence = self.semantic_disambiguator.target_for(
                source_field=source.source_field,
                spec=spec,
                field_rules=field_rules,
            )
            rule = "semantic_field_disambiguated" if target_field else None

        if not target_field:
            target_field = alias_mappings.get(source.normalized_source_field)
            rule = "alias_match" if target_field else None

        if not target_field and source.normalized_source_field in spec.columns:
            target_field = source.normalized_source_field
            rule = "exact_match"

        if not target_field:
            target_field, contextual_rule, _ = self.contextual_mapper.target_for(
                normalized_source=source.normalized_source_field,
                field_rules=field_rules,
            )
            rule = contextual_rule if target_field else None

        if not target_field or target_field not in spec.columns:
            return None

        field_rule = field_rules.get(target_field)
        type_compatibility = self.type_profiler.compatibility(
            source.value,
            getattr(field_rule, "field_type", None),
            target_field,
        )
        confidence = self.confidence_scorer.score(
            rule=rule or "unmapped",
            type_compatibility=type_compatibility,
        )
        if semantic_confidence:
            confidence = max(confidence, semantic_confidence)
        warning = self.confidence_scorer.warning_for(
            target_field=target_field,
            confidence=confidence,
        )
        return FieldCandidate(
            target_field=target_field,
            source_field=source.source_field,
            normalized_source_field=source.normalized_source_field,
            source_value=source.value,
            rule=rule or "unmapped",
            confidence=confidence,
            warning=warning,
        )

    def _learned_mappings(self, *, company_id: str | None, import_type: str) -> dict[str, str]:
        if not company_id:
            return {}
        rows = self.control.get_company_field_mappings(
            company_id=company_id,
            import_type=import_type,
        )
        return {
            str(row["normalized_source_field"]): str(row["target_field"])
            for row in rows
            if row.get("normalized_source_field") and row.get("target_field")
        }

    def _alias_mappings(self, field_rules: dict[str, Any]) -> dict[str, str]:
        mappings: dict[str, str] = {}
        for field_name, rule in field_rules.items():
            mappings.setdefault(compact_field_name(field_name), field_name)
            for alias in getattr(rule, "aliases", ()):
                mappings.setdefault(compact_field_name(alias), field_name)
        return mappings

    def _should_replace(
        self,
        *,
        current: FieldCandidate | None,
        candidate: FieldCandidate,
    ) -> bool:
        if current is None:
            return True
        if self._is_empty_value(current.source_value) and not self._is_empty_value(
            candidate.source_value
        ):
            return True
        if self._is_empty_value(candidate.source_value):
            return False
        return candidate.confidence > current.confidence

    def _is_empty_value(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        return False

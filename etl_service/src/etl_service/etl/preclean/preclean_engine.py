from __future__ import annotations

from typing import Any

from etl_service.domain.models import ImportSpec
from etl_service.etl.preclean.data_normalizer import DataNormalizer
from etl_service.etl.preclean.field_mapping_engine import FieldMappingEngine
from etl_service.etl.preclean.header_normalizer import HeaderNormalizer
from etl_service.etl.preclean.models import (
    FieldTrace,
    InterpretationWarning,
    InterpretedRow,
)
from etl_service.etl.preclean.relationship_resolver import RelationshipResolver
from etl_service.etl.preclean.row_confidence import RowConfidenceEvaluator
from etl_service.etl.preclean.semantic_value_normalizer import SemanticValueNormalizer
from etl_service.repositories.control_repository import ControlRepository
from etl_service.repositories.dw_repository import DwRepository


class PreCleanEngine:
    def __init__(self, *, control: ControlRepository, dw: DwRepository) -> None:
        self.header_normalizer = HeaderNormalizer()
        self.data_normalizer = DataNormalizer()
        self.field_mapping = FieldMappingEngine(control)
        self.semantic_normalizer = SemanticValueNormalizer()
        self.relationship_resolver = RelationshipResolver(dw)
        self.row_confidence = RowConfidenceEvaluator()

    def prepare(
        self,
        *,
        raw_data: dict[str, Any],
        spec: ImportSpec,
        company_id: str | None,
        field_rules: dict[str, Any],
        relation_rules: tuple[Any, ...],
    ) -> InterpretedRow:
        source_fields = self.header_normalizer.source_fields(raw_data)
        mapping = self.field_mapping.map_fields(
            source_fields=source_fields,
            spec=spec,
            company_id=company_id,
            field_rules=field_rules,
        )
        normalized_values = self.data_normalizer.normalize(mapping.mapped_data, field_rules)
        normalized_trace = self._with_final_values(
            mapping.mapping_trace,
            normalized_values,
            rule_suffix=None,
        )
        semantic_values, semantic_traces, semantic_warnings, semantic_confidence = (
            self.semantic_normalizer.normalize(
                import_type=spec.import_type,
                data=normalized_values,
                field_rules=field_rules,
                confidence=mapping.confidence,
            )
        )

        relationship_input = dict(semantic_values)
        for source in source_fields:
            relationship_input.setdefault(
                source.normalized_source_field,
                self.data_normalizer.normalize_value(source.value),
            )

        relationship = self.relationship_resolver.resolve(
            data=relationship_input,
            company_id=company_id,
            relation_rules=relation_rules,
        )
        clean_candidate = {
            key: value
            for key, value in relationship.resolved_data.items()
            if key in spec.columns or key in field_rules
        }
        confidence = dict(mapping.confidence)
        confidence.update(semantic_confidence)
        confidence.update(relationship.confidence)
        row_traces, row_warnings, row_confidence = self.row_confidence.evaluate(
            clean_candidate=clean_candidate,
            field_rules=field_rules,
            confidence=confidence,
        )
        confidence.update(row_confidence)
        warnings = [
            *mapping.warnings,
            *semantic_warnings,
            *relationship.warnings,
            *self._required_field_warnings(
                clean_candidate=clean_candidate,
                field_rules=field_rules,
                unmapped_fields=mapping.unmapped_fields,
            ),
            *row_warnings,
        ]

        return InterpretedRow(
            clean_candidate=clean_candidate,
            mapping_trace=[
                *normalized_trace,
                *semantic_traces,
                *relationship.mapping_trace,
                *row_traces,
            ],
            unmapped_fields=mapping.unmapped_fields,
            warnings=warnings,
            confidence=confidence,
        )

    def _with_final_values(
        self,
        traces: list[FieldTrace],
        final_values: dict[str, Any],
        rule_suffix: str | None,
    ) -> list[FieldTrace]:
        updated: list[FieldTrace] = []
        for trace in traces:
            final_value = final_values.get(trace.target_field, trace.final_value)
            rule = f"{trace.rule}_{rule_suffix}" if rule_suffix else trace.rule
            updated.append(
                FieldTrace(
                    target_field=trace.target_field,
                    source_field=trace.source_field,
                    source_value=trace.source_value,
                    final_value=final_value,
                    rule=rule,
                    confidence=trace.confidence,
                    warning=trace.warning,
                )
            )
        return updated

    def _required_field_warnings(
        self,
        *,
        clean_candidate: dict[str, Any],
        field_rules: dict[str, Any],
        unmapped_fields: dict[str, Any],
    ) -> list[InterpretationWarning]:
        warnings: list[InterpretationWarning] = []
        if not unmapped_fields:
            return warnings

        available_columns = ", ".join(sorted(unmapped_fields.keys())[:8])
        for field_name, rule in field_rules.items():
            if not getattr(rule, "required", False):
                continue
            if clean_candidate.get(field_name) in (None, ""):
                warnings.append(
                    InterpretationWarning(
                        field_name=field_name,
                        warning_type="REQUIRED_FIELD_NOT_INTERPRETED",
                        message=(
                            f"Required field {field_name} was not interpreted. "
                            f"Available unmapped columns: {available_columns}."
                        ),
                    )
                )
        return warnings

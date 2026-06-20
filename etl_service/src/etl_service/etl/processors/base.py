from dataclasses import dataclass
import json
from typing import Any, Literal

from sqlalchemy.exc import SQLAlchemyError

from etl_service.domain.enums import ErrorType
from etl_service.domain.models import ImportSpec, ValidationError
from etl_service.domain.process import LoadStats
from etl_service.etl.preclean import PreCleanEngine
from etl_service.etl.utils.errors import add_error
from etl_service.etl.utils.parsing import (
    get_value,
    parse_boolean,
    parse_date,
    parse_enum,
    parse_numeric,
    parse_string,
    parse_timestamp,
    parse_uuid,
)
from etl_service.etl.utils.validation import required
from etl_service.repositories.control_repository import ControlRepository
from etl_service.repositories.dw_repository import DwRepository
from etl_service.repositories.staging_repository import StagingRepository


FieldType = Literal["string", "numeric", "date", "timestamp", "boolean", "enum", "uuid"]


@dataclass(frozen=True)
class FieldRule:
    aliases: tuple[str, ...]
    field_type: FieldType = "string"
    required: bool = False
    enum_values: tuple[str, ...] = ()
    default: Any = None


@dataclass(frozen=True)
class RelationRule:
    field_name: str
    table_name: str
    pk_column: str


class BaseProcessor:
    import_type: str
    field_rules: dict[str, FieldRule] = {}
    relation_rules: tuple[RelationRule, ...] = ()

    def __init__(
        self,
        *,
        spec: ImportSpec,
        company_id: str | None,
        staging: StagingRepository,
        control: ControlRepository,
        dw: DwRepository,
        batch_size: int,
    ) -> None:
        self.spec = spec
        self.company_id = company_id
        self.staging = staging
        self.control = control
        self.dw = dw
        self.batch_size = batch_size
        self.preclean = PreCleanEngine(control=control, dw=dw)

    def process(self, *, import_id: str) -> LoadStats:
        stats = LoadStats()

        while True:
            rows = self.staging.fetch_pending_rows(
                import_id=import_id,
                spec=self.spec,
                limit=self.batch_size,
            )
            if not rows:
                break

            for row in rows:
                self._process_row(import_id=import_id, row=row, stats=stats)

        return stats

    def process_rows(self, *, import_id: str, staging_ids: list[str]) -> LoadStats:
        stats = LoadStats()
        rows = self.staging.fetch_pending_rows_by_ids(
            import_id=import_id,
            spec=self.spec,
            staging_ids=staging_ids,
        )
        for row in rows:
            self._process_row(import_id=import_id, row=row, stats=stats)
        return stats

    def normalize(
        self,
        raw_data: dict[str, Any],
        row_number: int,
    ) -> tuple[dict[str, Any], list[ValidationError]]:
        clean_data = dict(self.spec.default_values)
        errors: list[ValidationError] = []

        for field_name, rule in self.field_rules.items():
            raw_value = get_value(raw_data, (field_name, *rule.aliases), default=rule.default)
            if field_name == "company_id" and self.spec.force_company_id and self.company_id:
                raw_value = self.company_id
            if (
                field_name == "company_id_fk"
                and self.spec.dw_table == "inventory"
                and self.company_id
            ):
                raw_value = self.company_id
            try:
                parsed_value = self._parse_value(
                    field_name=field_name,
                    value=raw_value,
                    rule=rule,
                )
            except ValueError as exc:
                add_error(
                    errors,
                    row_number=row_number,
                    field_name=field_name,
                    field_value=raw_value,
                    error_type=ErrorType.DATA_TYPE,
                    message=str(exc),
                    expected_format=rule.field_type,
                    suggested_fix=f"Verify the value for {field_name}.",
                )
                parsed_value = None

            if parsed_value is not None:
                clean_data[field_name] = parsed_value

            if rule.required:
                required(
                    errors,
                    row_number=row_number,
                    value=clean_data.get(field_name),
                    field_name=field_name,
                )

        if self.spec.force_company_id and self.company_id:
            clean_data["company_id"] = self.company_id
        if self.spec.dw_table == "inventory" and self.company_id:
            clean_data.setdefault("company_id_fk", self.company_id)

        self.validate_relations(clean_data=clean_data, row_number=row_number, errors=errors)
        self.validate_business_rules(clean_data=clean_data, row_number=row_number, errors=errors)

        return {
            key: value
            for key, value in clean_data.items()
            if key in self.spec.columns and value is not None
        }, errors

    def validate_business_rules(
        self,
        *,
        clean_data: dict[str, Any],
        row_number: int,
        errors: list[ValidationError],
    ) -> None:
        return None

    def validate_relations(
        self,
        *,
        clean_data: dict[str, Any],
        row_number: int,
        errors: list[ValidationError],
    ) -> None:
        for relation in self.relation_rules:
            value = clean_data.get(relation.field_name)
            if value in (None, ""):
                continue
            if not self.dw.record_exists(
                table_name=relation.table_name,
                pk_column=relation.pk_column,
                value=value,
            ):
                add_error(
                    errors,
                    row_number=row_number,
                    field_name=relation.field_name,
                    field_value=value,
                    error_type=ErrorType.FK_VIOLATION,
                    message=(
                        f"{relation.field_name} does not exist in "
                        f"{relation.table_name}.{relation.pk_column}."
                    ),
                    expected_format="existing DW reference",
                    suggested_fix="Load or correct the referenced record first.",
                )

    def _process_row(self, *, import_id: str, row: dict[str, Any], stats: LoadStats) -> None:
        row_number = int(row["row_number"])
        raw_data = self._coerce_raw_data(row.get("raw_data"))
        try:
            interpreted = self.preclean.prepare(
                raw_data=raw_data,
                spec=self.spec,
                company_id=self.company_id,
                field_rules=self.field_rules,
                relation_rules=self.relation_rules,
            )
            self.control.insert_mapping_traces(
                import_id=import_id,
                row_number=row_number,
                import_type=self.spec.import_type,
                traces=[trace.as_dict() for trace in interpreted.mapping_trace],
                warnings=[warning.as_dict() for warning in interpreted.warnings],
            )
        except Exception as exc:
            errors: list[ValidationError] = []
            add_error(
                errors,
                row_number=row_number,
                field_name=None,
                error_type=ErrorType.BUSINESS_RULE,
                message=f"Could not interpret staging row: {type(exc).__name__}: {str(exc)[:800]}",
                suggested_fix="Review the staging raw_data structure and retry this row.",
            )
            self.control.insert_errors(import_id, errors)
            self.staging.mark_processed(
                spec=self.spec,
                staging_id=str(row["staging_id"]),
                clean_data={},
                errors=errors,
            )
            self.staging.session.commit()
            stats.add_failure()
            return

        clean_data, errors = self.normalize(interpreted.clean_candidate, row_number)

        if errors:
            self.control.insert_errors(import_id, errors)
            self.staging.mark_processed(
                spec=self.spec,
                staging_id=str(row["staging_id"]),
                clean_data=clean_data,
                errors=errors,
            )
            self.staging.session.commit()
            stats.add_failure()
            return

        try:
            _, action = self.dw.upsert_clean_row(spec=self.spec, clean_data=clean_data)
            self.staging.mark_processed(
                spec=self.spec,
                staging_id=str(row["staging_id"]),
                clean_data=clean_data,
                errors=[],
            )
            self.staging.session.commit()
            stats.add_success(action)
        except SQLAlchemyError as exc:
            self.staging.session.rollback()
            load_error = self._load_error(row_number=row_number, exc=exc)
            self.control.insert_errors(import_id, [load_error])
            self.staging.mark_processed(
                spec=self.spec,
                staging_id=str(row["staging_id"]),
                clean_data=clean_data,
                errors=[load_error],
            )
            self.staging.session.commit()
            stats.add_failure()
        except Exception as exc:
            self.staging.session.rollback()
            load_error = self._unexpected_error(row_number=row_number, exc=exc)
            self.control.insert_errors(import_id, [load_error])
            self.staging.mark_processed(
                spec=self.spec,
                staging_id=str(row["staging_id"]),
                clean_data=clean_data,
                errors=[load_error],
            )
            self.staging.session.commit()
            stats.add_failure()

    def _parse_value(self, *, field_name: str, value: Any, rule: FieldRule) -> Any:
        if value is None:
            return rule.default
        if rule.field_type == "string":
            return parse_string(value)
        if rule.field_type == "numeric":
            return parse_numeric(value)
        if rule.field_type == "date":
            return parse_date(value)
        if rule.field_type == "timestamp":
            return parse_timestamp(value)
        if rule.field_type == "boolean":
            return parse_boolean(value)
        if rule.field_type == "enum":
            return parse_enum(value, rule.enum_values)
        if rule.field_type == "uuid":
            return parse_uuid(value)
        raise ValueError(f"Unsupported parser for {field_name}: {rule.field_type}")

    def _coerce_raw_data(self, raw_data: Any) -> dict[str, Any]:
        if isinstance(raw_data, dict):
            return raw_data
        if isinstance(raw_data, str):
            try:
                parsed = json.loads(raw_data)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

    def _load_error(self, *, row_number: int, exc: SQLAlchemyError) -> ValidationError:
        message = str(exc.orig if getattr(exc, "orig", None) else exc)
        lowered = message.lower()
        if "foreign key" in lowered or "violates foreign key" in lowered:
            error_type = ErrorType.FK_VIOLATION
        elif "invalid input syntax" in lowered or "cannot cast" in lowered:
            error_type = ErrorType.DATA_TYPE
        elif "duplicate key" in lowered or "unique constraint" in lowered:
            error_type = ErrorType.DUPLICATE
        else:
            error_type = ErrorType.BUSINESS_RULE

        errors: list[ValidationError] = []
        add_error(
            errors,
            row_number=row_number,
            field_name=None,
            error_type=error_type,
            message=message[:1000],
            suggested_fix="Review the row data and database constraints.",
        )
        return errors[0]

    def _unexpected_error(self, *, row_number: int, exc: Exception) -> ValidationError:
        errors: list[ValidationError] = []
        add_error(
            errors,
            row_number=row_number,
            field_name=None,
            error_type=ErrorType.BUSINESS_RULE,
            message=f"{type(exc).__name__}: {str(exc)[:900]}",
            suggested_fix="Review this row and retry the import.",
        )
        return errors[0]

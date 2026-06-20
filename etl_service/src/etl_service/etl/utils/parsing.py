from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from etl_service.etl.preclean.header_normalizer import compact_field_name


TRUE_VALUES = {
    "true",
    "1",
    "si",
    "s",
    "yes",
    "y",
    "activo",
    "activa",
    "active",
    "verdadero",
    "operando",
    "operativa",
    "abierto",
    "abierta",
    "habilitado",
    "habilitada",
}
FALSE_VALUES = {
    "false",
    "0",
    "no",
    "n",
    "inactivo",
    "inactiva",
    "inactive",
    "cerrado",
    "cerrada",
    "deshabilitado",
    "deshabilitada",
    "falso",
}


def get_value(raw_data: dict[str, Any], aliases: tuple[str, ...], default: Any = None) -> Any:
    normalized = {_normalize_key(key): value for key, value in raw_data.items()}
    for alias in aliases:
        key = _normalize_key(alias)
        if key in normalized:
            return normalized[key]
    return default


def parse_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def parse_numeric(value: Any) -> Decimal | None:
    text = parse_string(value)
    if text is None:
        return None

    normalized = text.replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")

    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid numeric value: {value!r}") from None


def parse_date(value: Any) -> date | None:
    parsed = parse_timestamp(value)
    return parsed.date() if parsed else None


def parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    text = parse_string(value)
    if text is None:
        return None

    normalized = text.replace("/", "-")
    formats = (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    )
    for fmt in formats:
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(f"Invalid date/timestamp value: {value!r}") from None


def parse_boolean(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = parse_string(value)
    if text is None:
        return None
    lowered = text.lower()
    if lowered in TRUE_VALUES:
        return True
    if lowered in FALSE_VALUES:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}") from None


def parse_enum(value: Any, allowed_values: tuple[str, ...]) -> str | None:
    text = parse_string(value)
    if text is None:
        return None
    normalized = text.upper()
    if normalized not in allowed_values:
        raise ValueError(f"Invalid enum value: {value!r}")
    return normalized


def parse_uuid(value: Any) -> str | None:
    text = parse_string(value)
    if text is None:
        return None
    try:
        return str(UUID(text))
    except (TypeError, ValueError):
        raise ValueError(f"Invalid UUID value: {value!r}") from None


def _normalize_key(value: str) -> str:
    return compact_field_name(value)

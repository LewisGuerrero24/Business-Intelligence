from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any


EMPTY_VALUES = {""}

CURRENCY_PATTERN = re.compile(r"(?i)\b(cop|usd|eur|mxn|ars|clp|pen)\b|[$]")


class DataNormalizer:
    def normalize(
        self,
        data: dict[str, Any],
        field_rules: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            key: self.normalize_value(
                value,
                field_type=getattr((field_rules or {}).get(key), "field_type", None),
            )
            for key, value in data.items()
        }

    def normalize_value(self, value: Any, *, field_type: str | None = None) -> Any:
        if value is None:
            return None
        if isinstance(value, dict):
            return self.normalize(value)
        if isinstance(value, list):
            return [self.normalize_value(item, field_type=field_type) for item in value]
        if not isinstance(value, str):
            return value

        text = " ".join(value.strip().split())
        if text.lower() in EMPTY_VALUES:
            return None

        numeric_value = self._numeric_text(text) if field_type == "numeric" else None
        return numeric_value if numeric_value is not None else text

    def _numeric_text(self, value: str) -> str | None:
        if not any(char.isdigit() for char in value):
            return None

        cleaned = CURRENCY_PATTERN.sub("", value).strip()
        cleaned = cleaned.replace("%", "").replace(" ", "")
        if not re.fullmatch(r"[-+]?[0-9.,]+", cleaned):
            return None

        if "," in cleaned and "." in cleaned:
            decimal_separator = "," if cleaned.rfind(",") > cleaned.rfind(".") else "."
            thousands_separator = "." if decimal_separator == "," else ","
            cleaned = cleaned.replace(thousands_separator, "")
            cleaned = cleaned.replace(decimal_separator, ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")

        try:
            Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return None
        return cleaned

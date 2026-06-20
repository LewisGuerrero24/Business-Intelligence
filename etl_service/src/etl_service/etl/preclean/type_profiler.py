from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9\s().-]{5,}$")
CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_.-]{1,}$", re.IGNORECASE)


class TypeProfiler:
    def compatibility(self, value: Any, field_type: str | None, field_name: str) -> float:
        if value is None:
            return 0.5
        if isinstance(value, str) and not value.strip():
            return 0.4

        if field_type == "uuid":
            return 1.0 if self.looks_uuid(value) else 0.15
        if field_type == "numeric":
            return 1.0 if self.looks_numeric(value) else 0.25
        if field_type in {"date", "timestamp"}:
            return 1.0 if self.looks_date(value) else 0.35
        if field_type == "boolean":
            return 1.0 if self.looks_boolean(value) else 0.25
        if "email" in field_name:
            return 1.0 if self.looks_email(value) else 0.35
        if "phone" in field_name or "mobile" in field_name or "telefono" in field_name:
            return 1.0 if self.looks_phone(value) else 0.45
        if "code" in field_name or "sku" in field_name or "codigo" in field_name:
            return 0.95 if self.looks_code(value) else 0.65
        return 0.85

    def looks_uuid(self, value: Any) -> bool:
        try:
            UUID(str(value).strip())
        except (TypeError, ValueError):
            return False
        return True

    def looks_numeric(self, value: Any) -> bool:
        text = str(value).strip().replace(" ", "")
        if "," in text and "." in text:
            decimal_separator = "," if text.rfind(",") > text.rfind(".") else "."
            thousands_separator = "." if decimal_separator == "," else ","
            text = text.replace(thousands_separator, "").replace(decimal_separator, ".")
        elif "," in text:
            text = text.replace(",", ".")
        text = re.sub(r"(?i)\b(cop|usd|eur|mxn|ars|clp|pen)\b|[$]", "", text)
        text = text.replace("%", "")
        try:
            Decimal(text)
        except (InvalidOperation, ValueError):
            return False
        return True

    def looks_date(self, value: Any) -> bool:
        text = str(value).strip()
        return bool(re.search(r"\d{1,4}[-/]\d{1,2}[-/]\d{1,4}", text))

    def looks_boolean(self, value: Any) -> bool:
        text = str(value).strip().lower()
        return text in {
            "true",
            "false",
            "1",
            "0",
            "si",
            "s",
            "no",
            "n",
            "activo",
            "activa",
            "inactivo",
            "inactiva",
            "operando",
            "abierto",
            "abierta",
            "cerrado",
            "cerrada",
            "deshabilitado",
            "deshabilitada",
        }

    def looks_email(self, value: Any) -> bool:
        return bool(EMAIL_PATTERN.match(str(value).strip()))

    def looks_phone(self, value: Any) -> bool:
        return bool(PHONE_PATTERN.match(str(value).strip()))

    def looks_code(self, value: Any) -> bool:
        text = str(value).strip()
        return bool(CODE_PATTERN.match(text)) and len(text) <= 80

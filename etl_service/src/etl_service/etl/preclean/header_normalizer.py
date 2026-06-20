from __future__ import annotations

import re
import unicodedata
from typing import Any

from etl_service.etl.preclean.models import SourceField


SEPARATOR_PATTERN = re.compile(r"[\s_\-./\\:;|]+")
NON_WORD_PATTERN = re.compile(r"[^a-z0-9 ]+")


def normalize_field_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = _strip_accents(text)
    text = text.replace("&", " y ")
    text = SEPARATOR_PATTERN.sub(" ", text)
    text = NON_WORD_PATTERN.sub("", text)
    return " ".join(text.split())


def compact_field_name(value: Any) -> str:
    return normalize_field_name(value).replace(" ", "_")


class HeaderNormalizer:
    def normalize(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in raw_data.items():
            normalized_key = compact_field_name(key)
            if normalized_key and normalized_key not in normalized:
                normalized[normalized_key] = value
            normalized[str(key)] = value
        return normalized

    def source_fields(self, raw_data: dict[str, Any]) -> list[SourceField]:
        return [
            SourceField(
                source_field=str(key),
                normalized_source_field=compact_field_name(key),
                value=value,
            )
            for key, value in raw_data.items()
            if compact_field_name(key)
        ]


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))

from __future__ import annotations


BASE_CONFIDENCE = {
    "company_mapping": 0.99,
    "alias_match": 0.95,
    "exact_match": 0.93,
    "semantic_field_disambiguated": 0.94,
    "contextual_match": 0.84,
    "similarity_match": 0.72,
    "unmapped": 0.0,
}


class ConfidenceScorer:
    def score(self, *, rule: str, type_compatibility: float) -> float:
        base = BASE_CONFIDENCE.get(rule, 0.5)
        score = (base * 0.75) + (type_compatibility * 0.25)
        return round(max(0.0, min(score, 1.0)), 4)

    def warning_for(self, *, target_field: str, confidence: float) -> str | None:
        if confidence >= 0.9:
            return None
        if confidence >= 0.7:
            return f"Field {target_field} was inferred with medium confidence."
        return f"Field {target_field} was inferred with low confidence."

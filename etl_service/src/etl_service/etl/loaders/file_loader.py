from pathlib import Path
from typing import Any

import pandas as pd

from etl_service.domain.models import ExtractedRow
from etl_service.utils.chunks import chunked


def read_tabular_file(file_path: str | Path, chunk_size: int = 1000) -> list[ExtractedRow]:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path, dtype=str)
    elif suffix == ".csv":
        df = pd.read_csv(path, dtype=str)
    else:
        raise ValueError(f"Unsupported file extension: {suffix}")

    df = df.where(pd.notnull(df), None)
    extracted: list[ExtractedRow] = []

    for batch_index, batch in enumerate(chunked(df.to_dict(orient="records"), chunk_size), start=1):
        for offset, record in enumerate(batch):
            absolute_index = (batch_index - 1) * chunk_size + offset
            extracted.append(
                ExtractedRow(
                    row_number=absolute_index + 2,
                    raw_data=_normalize_record(record),
                    chunk_number=batch_index,
                )
            )

    return extracted


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    return {str(key).strip(): _normalize_value(value) for key, value in record.items()}


def _normalize_value(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned if cleaned != "" else None
    return value

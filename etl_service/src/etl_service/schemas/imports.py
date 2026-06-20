from uuid import UUID
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ImportFileRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "company_id": "55f58d0d-87a4-4bad-a60b-f5dadf08f924",
                    "import_type": "branches",
                    "file_path": (
                        "C:/Users/USUARIO/Documents/etl_service/test_files/"
                        "branches_messy_external.xlsx"
                    ),
                    "source_type": "excel",
                    "process_now": False,
                }
            ]
        }
    )

    company_id: UUID
    import_type: str
    file_path: str
    source_type: str = "excel"
    created_by: UUID | None = None
    process_now: bool = Field(default=False)


class ProcessImportRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "import_id": "00000000-0000-0000-0000-000000000000",
                }
            ]
        }
    )

    import_id: UUID


class ImportResult(BaseModel):
    import_id: str
    status: str
    total_records: int | None = None
    processed_records: int | None = None
    success_records: int | None = None
    failed_records: int | None = None
    staging_records: int | None = None
    inserted_records: int | None = None
    updated_records: int | None = None
    load_failed_records: int | None = None
    error_summary: dict | None = None


class CompanyImportErrorsResult(BaseModel):
    company_id: str
    import_id: str | None = None
    total_errors: int
    limit: int
    offset: int
    errors: list[dict[str, Any]]


class ImportErrorCorrectionResult(BaseModel):
    error_id: str
    import_id: str
    company_id: str
    import_type: str
    row_number: int
    staging_id: str
    fields_to_fix: list[str]
    errors: list[dict[str, Any]]
    raw_data: dict[str, Any]
    clean_data: dict[str, Any]
    correction_data: dict[str, Any]


class ApplyErrorCorrectionRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "company_id": "55f58d0d-87a4-4bad-a60b-f5dadf08f924",
                    "correction_data": {
                        "name": "Manizales Centro",
                        "code": "MAN-CEN-08",
                        "address": "Carrera 23 # 25-30",
                        "city": "Manizales",
                        "phone": "606 884 2210",
                        "is_active": True,
                    },
                }
            ]
        }
    )

    company_id: UUID
    correction_data: dict[str, Any]


class ApplyErrorCorrectionResponse(BaseModel):
    success: bool
    message: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

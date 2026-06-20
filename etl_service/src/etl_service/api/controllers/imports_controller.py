from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from etl_service.api.errors import (
    raise_database_error,
    raise_pydantic_error,
    raise_unexpected_error,
)
from etl_service.core.config import get_settings
from etl_service.db.connection import get_session
from etl_service.schemas.imports import (
    ImportFileRequest,
    ImportResult,
    ProcessImportRequest,
)
from etl_service.services.import_service import ImportService


router = APIRouter(tags=["imports"])


@router.post("/imports/file", response_model=ImportResult)
def import_file(
    payload: ImportFileRequest,
    session: Session = Depends(get_session),
) -> dict:
    settings = get_settings()
    service = ImportService(session, settings)
    try:
        return service.create_import_from_file(
            company_id=str(payload.company_id),
            import_type=payload.import_type,
            file_path=payload.file_path,
            source_type=payload.source_type,
            created_by=str(payload.created_by) if payload.created_by else None,
            process_now=payload.process_now,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise_database_error(exc, session)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"File not found: {exc.filename}") from exc
    except PydanticValidationError as exc:
        raise_pydantic_error(exc)
    except Exception as exc:
        raise_unexpected_error(exc, session)


@router.post("/imports/process", response_model=ImportResult)
def process_import(
    payload: ProcessImportRequest,
    session: Session = Depends(get_session),
) -> dict:
    settings = get_settings()
    service = ImportService(session, settings)
    try:
        return service.process_import(payload.import_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise_database_error(exc, session)
    except Exception as exc:
        raise_unexpected_error(exc, session)


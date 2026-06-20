from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from etl_service.api.errors import raise_database_error, raise_unexpected_error
from etl_service.core.config import get_settings
from etl_service.db.connection import get_session
from etl_service.repositories.control_repository import ControlRepository
from etl_service.schemas.imports import (
    ApplyErrorCorrectionRequest,
    ApplyErrorCorrectionResponse,
    CompanyImportErrorsResult,
    ImportErrorCorrectionResult,
)
from etl_service.services.correction_service import CorrectionService


router = APIRouter(tags=["import errors"])


@router.get("/imports/{import_id}/import-errors", response_model=CompanyImportErrorsResult)
def import_error_list(
    import_id: UUID,
    import_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
) -> dict:
    _validate_pagination(limit=limit, offset=offset)
    settings = get_settings()
    control = ControlRepository(session, settings)
    try:
        import_info = control.get_import(import_id)
        total_errors = control.count_company_errors(
            company_id=import_info["company_id"],
            import_id=import_id,
            import_type=import_type,
        )
        errors = control.list_company_errors(
            company_id=import_info["company_id"],
            import_id=import_id,
            import_type=import_type,
            limit=limit,
            offset=offset,
        )
        return {
            "company_id": str(import_info["company_id"]),
            "import_id": str(import_id),
            "total_errors": total_errors,
            "limit": limit,
            "offset": offset,
            "errors": errors,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise_database_error(exc)


@router.get(
    "/import-errors/{error_id}/correction",
    response_model=ImportErrorCorrectionResult,
)
def import_error_correction(
    error_id: UUID,
    company_id: UUID | None = None,
    session: Session = Depends(get_session),
) -> dict:
    settings = get_settings()
    service = CorrectionService(session, settings)
    try:
        return service.get_correction_by_error(error_id=error_id, company_id=company_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise_database_error(exc)
    except Exception as exc:
        raise_unexpected_error(exc)


@router.post(
    "/import-errors/{error_id}/correction",
    response_model=ApplyErrorCorrectionResponse,
)
def apply_import_error_correction(
    error_id: UUID,
    payload: ApplyErrorCorrectionRequest,
    session: Session = Depends(get_session),
) -> dict:
    settings = get_settings()
    service = CorrectionService(session, settings)
    try:
        return service.apply_correction_by_error(
            error_id=error_id,
            company_id=payload.company_id,
            correction_data=payload.correction_data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise_database_error(exc, session)
    except Exception as exc:
        raise_unexpected_error(exc, session)


def _validate_pagination(*, limit: int, offset: int) -> None:
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be greater than or equal to 0")

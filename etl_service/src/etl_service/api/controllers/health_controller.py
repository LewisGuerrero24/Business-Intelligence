from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from etl_service.core.config import get_settings
from etl_service.db.connection import check_database_connection, get_session


router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "app": settings.app_name}


@router.get("/health/db")
def database_health(session: Session = Depends(get_session)) -> dict[str, str]:
    return check_database_connection(session)

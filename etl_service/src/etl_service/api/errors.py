from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def raise_database_error(exc: SQLAlchemyError, session: Session | None = None) -> None:
    if session is not None:
        session.rollback()
    raise HTTPException(status_code=500, detail=database_error_message(exc)) from exc


def raise_unexpected_error(exc: Exception, session: Session | None = None) -> None:
    if session is not None:
        session.rollback()
    raise HTTPException(status_code=500, detail=unexpected_error_message(exc)) from exc


def raise_pydantic_error(exc: PydanticValidationError) -> None:
    raise HTTPException(status_code=400, detail=exc.errors()) from exc


def database_error_message(exc: SQLAlchemyError) -> str:
    original = getattr(exc, "orig", None)
    base_message = str(original or exc).splitlines()[0]
    details: list[str] = [base_message]

    diagnostic = getattr(original, "diag", None)
    for attr in ("message_detail", "message_hint", "context"):
        value = getattr(diagnostic, attr, None) if diagnostic else None
        if value:
            details.append(str(value))

    return " | ".join(details)


def unexpected_error_message(exc: Exception) -> str:
    return f"{type(exc).__name__}: {str(exc).splitlines()[0]}"


def validation_error_response(exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    json_errors = [error for error in errors if error.get("type") == "json_invalid"]
    if json_errors:
        first_error = json_errors[0]
        position = _json_error_position(first_error)
        return JSONResponse(
            status_code=422,
            content={
                "detail": "El cuerpo de la solicitud no es JSON valido.",
                "position": position,
                "hint": (
                    "Revisa comillas dobles, comas entre campos, valores booleanos "
                    "true/false sin comillas, y que no haya texto fuera del objeto JSON."
                ),
                "valid_example": {
                    "company_id": "55f58d0d-87a4-4bad-a60b-f5dadf08f924",
                    "import_type": "branches",
                    "file_path": (
                        "C:/Users/USUARIO/Documents/etl_service/test_files/"
                        "branches_messy_external.xlsx"
                    ),
                    "source_type": "excel",
                    "process_now": False,
                },
            },
        )

    return JSONResponse(status_code=422, content={"detail": errors})


def _json_error_position(error: dict) -> int | None:
    location = error.get("loc") or []
    if len(location) >= 2 and location[0] == "body" and isinstance(location[1], int):
        return location[1]
    return None

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from etl_service.api.controllers import (
    health_router,
    import_errors_router,
    imports_router,
)
from etl_service.api.errors import validation_error_response
from etl_service.core.config import get_settings
from etl_service.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return validation_error_response(exc)

    app.include_router(health_router)
    app.include_router(imports_router)
    app.include_router(import_errors_router)

    return app


app = create_app()

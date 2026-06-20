from pathlib import Path

import typer
from pydantic import ValidationError

from etl_service.core.config import get_settings
from etl_service.core.logging import configure_logging
from etl_service.etl.registry import IMPORT_SPECS
from etl_service.workers.console_progress import ConsoleProcessReporter, humanize_key

app = typer.Typer(no_args_is_help=True)


def _settings_or_exit():
    try:
        return get_settings()
    except ValidationError as exc:
        message = exc.errors()[0].get("msg", str(exc))
        typer.secho(f"Configuration error: {message}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


@app.command("check-db")
def check_db() -> None:
    configure_logging()
    _settings_or_exit()
    from etl_service.db.connection import SessionLocal, check_database_connection

    with SessionLocal() as session:
        result = check_database_connection(session)
    typer.echo(result)


@app.command("list-types")
def list_types() -> None:
    for import_type in sorted(IMPORT_SPECS):
        typer.echo(import_type)


@app.command("import-file")
def import_file(
    company_id: str = typer.Option(...),
    import_type: str = typer.Option(...),
    file_path: Path = typer.Option(..., exists=True, readable=True),
    source_type: str = typer.Option("excel"),
    created_by: str | None = typer.Option(None),
    process: bool = typer.Option(False),
) -> None:
    configure_logging()
    settings = _settings_or_exit()
    from etl_service.db.connection import SessionLocal
    from etl_service.services.import_service import ImportService

    with SessionLocal() as session:
        service = ImportService(session, settings, reporter=ConsoleProcessReporter())
        result = service.create_import_from_file(
            company_id=company_id,
            import_type=import_type,
            file_path=file_path,
            source_type=source_type,
            created_by=created_by,
            process_now=process,
        )
    _echo_result(result)


@app.command("process")
def process_import(import_id: str = typer.Option(...)) -> None:
    configure_logging()
    settings = _settings_or_exit()
    from etl_service.db.connection import SessionLocal
    from etl_service.services.import_service import ImportService

    with SessionLocal() as session:
        service = ImportService(session, settings, reporter=ConsoleProcessReporter())
        result = service.process_import(import_id)
    _echo_result(result)


def _echo_result(result: dict) -> None:
    typer.secho("\nResumen", fg=typer.colors.BLUE, bold=True)
    for key, value in result.items():
        if value is not None:
            typer.echo(f"  {humanize_key(key)}: {value}")

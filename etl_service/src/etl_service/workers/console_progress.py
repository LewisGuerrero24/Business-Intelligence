from typing import Any

import typer


class ConsoleProcessReporter:
    def __init__(self) -> None:
        self._step_number = 0

    def step(self, message: str, **context: Any) -> None:
        self._step_number += 1
        typer.secho(f"\n[{self._step_number}] {message}", fg=typer.colors.CYAN, bold=True)
        self._write_context(context)

    def success(self, message: str, **context: Any) -> None:
        typer.secho(f"    OK: {message}", fg=typer.colors.GREEN)
        self._write_context(context)

    def warning(self, message: str, **context: Any) -> None:
        typer.secho(f"    Aviso: {message}", fg=typer.colors.YELLOW)
        self._write_context(context)

    def error(self, message: str, **context: Any) -> None:
        typer.secho(f"    Error: {message}", fg=typer.colors.RED, err=True)
        self._write_context(context, err=True)

    def _write_context(self, context: dict[str, Any], *, err: bool = False) -> None:
        for key, value in context.items():
            if value is None:
                continue
            typer.echo(f"    {humanize_key(key)}: {value}", err=err)


def humanize_key(key: str) -> str:
    labels = {
        "import_id": "importacion",
        "import_type": "tipo",
        "company_id": "empresa",
        "file_path": "archivo",
        "source_type": "origen",
        "total_records": "registros totales",
        "staging_records": "registros en staging",
        "read_records": "registros leidos",
        "valid_records": "registros validos",
        "invalid_records": "registros invalidos",
        "inserted_records": "registros insertados",
        "updated_records": "registros actualizados",
        "failed_records": "registros con error",
        "load_failed_records": "errores durante carga",
        "error_count": "errores encontrados",
        "status": "estado",
    }
    return labels.get(key, key.replace("_", " "))

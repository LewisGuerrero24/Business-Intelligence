from typing import Any, Protocol


class ProcessReporter(Protocol):
    def step(self, message: str, **context: Any) -> None:
        """Report that a process step started or advanced."""

    def success(self, message: str, **context: Any) -> None:
        """Report that a process step finished successfully."""

    def warning(self, message: str, **context: Any) -> None:
        """Report a recoverable problem."""

    def error(self, message: str, **context: Any) -> None:
        """Report a process error."""


class NullProcessReporter:
    def step(self, message: str, **context: Any) -> None:
        pass

    def success(self, message: str, **context: Any) -> None:
        pass

    def warning(self, message: str, **context: Any) -> None:
        pass

    def error(self, message: str, **context: Any) -> None:
        pass

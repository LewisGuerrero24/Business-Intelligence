from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationStats:
    read_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    error_count: int = 0

    def add_result(self, errors: list[Any]) -> None:
        self.read_records += 1
        if errors:
            self.invalid_records += 1
            self.error_count += len(errors)
        else:
            self.valid_records += 1


@dataclass
class LoadStats:
    read_records: int = 0
    inserted_records: int = 0
    updated_records: int = 0
    failed_records: int = 0

    @property
    def success_records(self) -> int:
        return self.inserted_records + self.updated_records

    def add_success(self, action: str) -> None:
        self.read_records += 1
        if action == "updated":
            self.updated_records += 1
        else:
            self.inserted_records += 1

    def add_failure(self) -> None:
        self.read_records += 1
        self.failed_records += 1

from enum import StrEnum


class ImportStatus(StrEnum):
    PENDING = "PENDING"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class SourceType(StrEnum):
    EXCEL = "excel"
    CSV = "csv"
    API = "api"
    MANUAL = "manual"


class ErrorType(StrEnum):
    VALIDATION = "VALIDATION"
    DUPLICATE = "DUPLICATE"
    FK_VIOLATION = "FK_VIOLATION"
    DATA_TYPE = "DATA_TYPE"
    REQUIRED_FIELD = "REQUIRED_FIELD"
    BUSINESS_RULE = "BUSINESS_RULE"


class Severity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


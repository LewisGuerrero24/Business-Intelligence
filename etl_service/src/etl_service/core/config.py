from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "etl-service"
    app_env: str = "local"
    log_level: str = "INFO"

    postgres_host: str = "100.77.28.104"
    postgres_port: int = 5432
    postgres_db: str = "postgres"
    postgres_user: str = "administrador"
    postgres_password: str = Field(default="", repr=False)
    database_url: str | None = Field(default=None, repr=False)

    dw_schema: str = "public"
    control_schema: str = "Control"
    staging_schema: str = "Staging"

    default_batch_size: int = 1000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_database_credentials(self) -> "Settings":
        if self.database_url:
            return self

        invalid_passwords = {"", "replace_with_real_password"}
        if self.postgres_password in invalid_passwords:
            raise ValueError(
                "POSTGRES_PASSWORD must be set in .env with the real PostgreSQL password, "
                "or DATABASE_URL must be provided."
            )

        return self

    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url

        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        host = self.postgres_host
        port = self.postgres_port
        db = quote_plus(self.postgres_db)
        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()

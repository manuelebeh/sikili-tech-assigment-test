from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application and integration settings from the environment (never hardcode secrets)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str | None = Field(
        default=None,
        validation_alias="DATABASE_URL",
        description="Full SQLAlchemy URL; overrides PG* when set.",
    )

    pghost: str = Field(default="localhost", validation_alias="PGHOST")
    pgport: int = Field(default=5432, validation_alias="PGPORT")
    pguser: str = Field(default="odoo", validation_alias="PGUSER")
    pgpassword: str = Field(default="", validation_alias="PGPASSWORD")
    pgdatabase: str = Field(default="postgres", validation_alias="PGDATABASE")

    odoo_url: str = Field(
        default="http://localhost:8069",
        validation_alias="ODOO_URL",
        description="Base URL for Odoo (XML-RPC / HTTP).",
    )

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        user = quote_plus(self.pguser)
        password = quote_plus(self.pgpassword)
        return (
            f"postgresql+psycopg://{user}:{password}"
            f"@{self.pghost}:{self.pgport}/{self.pgdatabase}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

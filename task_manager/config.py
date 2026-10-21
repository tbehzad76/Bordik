from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Task Manager"
    database_url: str = "sqlite:///./tasks.db"
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)
    cookie_secure: bool = False
    auto_create_tables: bool = True

    @field_validator("jwt_secret_key")
    @classmethod
    def reject_placeholder_secret(cls, value: str) -> str:
        if value.strip().lower() in {"change-me", "secret", "changeme"}:
            raise ValueError("JWT_SECRET_KEY must be a strong random value")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

from __future__ import annotations

import os
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/employee_directory"
    SECRET_KEY: str = "change-me-in-production"
    FLASK_ENV: str = "development"
    JWT_SECRET_KEY: str = "jwt-change-me-in-production"
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES: int = 60
    UPLOAD_FOLDER: str = "/uploads"
    MAX_CONTENT_LENGTH_MB: int = 5
    ALLOWED_EXTENSIONS: ClassVar[set[str]] = {"png", "jpg", "jpeg", "gif", "webp"}

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return self.DATABASE_URL

    @property
    def MAX_CONTENT_LENGTH(self) -> int:
        return self.MAX_CONTENT_LENGTH_MB * 1024 * 1024


settings = Settings()

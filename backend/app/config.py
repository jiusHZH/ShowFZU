from __future__ import annotations

import json
from functools import lru_cache
from typing import Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ShowFZU API"
    env: str = "development"
    database_url: str = Field(default="sqlite:///./showfzu.dev.db")
    session_secret: str = "replace-me"
    session_cookie_name: str = "showfzu_session"
    session_max_age_seconds: int = 60 * 60 * 24 * 7
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])
    public_base_url: str = "http://127.0.0.1:5173"
    supabase_url: str | None = None
    supabase_service_key: str | None = None
    storage_posts_bucket: str = "post-media"
    storage_avatars_bucket: str = "avatars"
    storage_guide_bucket: str = "official-guide"
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    secure_cookies: bool = False

    model_config = SettingsConfigDict(
        env_prefix="SHOWFZU_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        enable_decoding=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed.startswith("["):
                return json.loads(trimmed)
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_config(self) -> Self:
        if not self.is_production:
            return self

        if self.database_url.strip().lower().startswith("sqlite"):
            raise ValueError("Production requires SHOWFZU_DATABASE_URL to point to Supabase Postgres.")
        if not self.session_secret or self.session_secret == "replace-me":
            raise ValueError("Production requires SHOWFZU_SESSION_SECRET to be set to a strong secret.")
        if not self.supabase_url:
            raise ValueError("Production requires SHOWFZU_SUPABASE_URL.")
        if not self.supabase_service_key:
            raise ValueError("Production requires SHOWFZU_SUPABASE_SERVICE_KEY for backend Storage access.")

        return self

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def default_cover_url(self) -> str:
        return f"{self.public_base_url.rstrip('/')}/default-cover.svg"

    @property
    def storage_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()

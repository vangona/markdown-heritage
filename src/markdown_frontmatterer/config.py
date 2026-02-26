"""Application settings loaded from environment variables / .env file."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_api_key: str = ""
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "google/gemini-flash-1.5"
    llm_max_content_chars: int = 12_000
    concurrency: int = 5
    max_retries: int = 3
    mdfm_lang: str = "en"
    instagram_session_dir: str = ""  # Custom instaloader session directory
    vision_max_images: int = 5
    vision_detail: str = "low"


settings = Settings()

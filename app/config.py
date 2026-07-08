"""Configuration module for ArenaMate.

Loads environment variables using pydantic-settings, falling back to safe defaults.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration and credentials.

    Attributes:
        app_name (str): The name of the application. Defaults to "ArenaMate".
        gemini_api_key (str | None): Google Gemini API Key for phrasing.
        gemini_model (str): Google Gemini model identifier.
        gemini_max_output_tokens (int): Maximum output tokens for response caps.
        allowed_origins (list[str]): List of allowed origins for CORS policy.
        rate_limit_capacity (int): Burst limit capacity for per-IP rate limiting.
        rate_limit_refill_per_sec (float): Tokens refilled per second for rate limiting.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ArenaMate"

    # Gemini configurations
    gemini_api_key: str | None = Field(default=None, description="Google Gemini API Key")
    gemini_model: str = Field(default="gemini-1.5-flash")
    gemini_max_output_tokens: int = Field(default=256, ge=16, le=2048)

    # CORS settings
    allowed_origins: list[str] = Field(
        default=["http://localhost:8000", "http://127.0.0.1:8000"],
        description="List of allowed origins for CORS policy",
    )

    # Rate Limiting (Token Bucket)
    rate_limit_capacity: int = Field(default=30, ge=1)
    rate_limit_refill_per_sec: float = Field(default=0.5, ge=0.0)

    @property
    def gemini_enabled(self) -> bool:
        """Helper checking if Gemini is active.

        Returns:
            bool: True if a valid Gemini API key is configured, False otherwise.
        """
        return bool(self.gemini_api_key and self.gemini_api_key.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return process-wide cached settings singleton.

    Returns:
        Settings: The cached Settings instance.
    """
    return Settings()

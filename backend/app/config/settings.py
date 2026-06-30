"""Application configuration via environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    cerebras_api_key: str = ""
    cerebras_base_url: str = "https://api.cerebras.ai/v1"
    model_name: str = "llama-3.3-70b"
    whisper_model: str = "base"

    # Agent
    intent_confidence_threshold: float = 0.65
    max_retries: int = 3
    tool_timeout_seconds: int = 120
    max_upload_size_mb: int = 50

    # Paths
    upload_dir: Path = Path("/tmp/uploads")
    trace_dir: Path = Path("/tmp/traces")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    debug: bool = False

    # Pricing (USD per 1M tokens) for cost estimator
    input_token_price: float = 0.85
    output_token_price: float = 1.20

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()

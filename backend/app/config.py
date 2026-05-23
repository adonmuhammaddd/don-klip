from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://app:app@postgres:5432/clipper"

    # Storage (mounted volumes)
    uploads_dir: str = "/data/uploads"
    outputs_dir: str = "/data/outputs"
    whisper_models_dir: str = "/data/models"

    # Whisper
    whisper_model: str = "base.en"
    whisper_bin: str = "/usr/local/bin/whisper-cli"

    # LLM
    llm_provider: Literal["gemini", "ollama", "claude", "openai"] = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    ollama_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.1:8b"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Twitch (chat replay)
    twitch_client_id: str = "kimne78kx3ncx6brgo4mv6wki5h1ko"

    # Detection defaults
    audio_spike_std_multiplier: float = 2.0
    max_candidates_per_job: int = 50

    # Limits
    max_upload_mb: int = 4096
    max_video_duration_sec: int = 14400

    # yt-dlp
    yt_dlp_cookies: str = ""

    # CORS (comma-separated)
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

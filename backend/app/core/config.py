from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    storage_dir: Path = Path("./storage")
    ttl_seconds: int = 600
    max_image_bytes: int = 10 * 1024 * 1024
    max_image_dim: int = 2048

    ai_base_url: str = "http://localhost:8001"
    ai_timeout_seconds: int = 60
    ai_client_mode: str = "mock"

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()

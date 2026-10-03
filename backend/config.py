"""App settings, loaded from env vars or local .env file"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env" , env_prefix="FOOD_INTAKE_", extra="ignore"
    )

    app_name : str = "Food Intake API"
    app_env : str = "development"

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'food_intake.db').as_posix()}"
    log_level: str = "DEBUG"

    cors_origins: list[str] = ["http://localhost:8080","http://127.0.0.1:8080"]
    max_range_days: int = 366
    default_page_size : int = 100
    max_page_size : int = 500

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
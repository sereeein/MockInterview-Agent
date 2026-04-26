from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    db_url: str = "sqlite:///./data/app.db"
    cors_origins: list[str] = ["http://localhost:3000"]
    claude_model: str = "claude-opus-4-7"
    seed_user_id: int = 1


@lru_cache
def get_settings() -> Settings:
    return Settings()

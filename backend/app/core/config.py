from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DivinationEngine"
    database_url: str = "sqlite:///./divination.db"
    model_config = SettingsConfigDict(env_prefix="DIVINATION_", env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()

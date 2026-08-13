from functools import lru_cache

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "El Cercho API"
    environment: str = "dev"
    release: str = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    jwt_secret_key: str = Field(min_length=32)
    jwt_issuer: str = "el-cercho-api"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    cors_origins: list[str] = []
    sentry_dsn: str = ""
    email_backend: str = "log"
    email_from: str = "hola@elcercho.mx"
    mailhog_host: str = "mailhog"
    mailhog_port: int = 1025
    seed_admin_email: str = "hugo@elcercho.mx"
    seed_admin_password: str = "Admin123!"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


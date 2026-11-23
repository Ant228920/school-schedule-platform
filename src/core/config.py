import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

APP_ENV = os.getenv("APP_ENV", "sandbox").strip().lower()

target_env_file = BASE_DIR / f".env.{APP_ENV}"

if not target_env_file.exists():
    target_env_file = BASE_DIR / ".env"


class Settings(BaseSettings):
    ENVIRONMENT: str = APP_ENV
    DEBUG: bool = True

    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str

    DB_POOL_SIZE: int = 15
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 5
    DB_POOL_RECYCLE: int = 1800
    REDIS_URL: str = ""
    CACHE_TTL_USER: int = 60
    CACHE_TTL_SCHEDULE: int = 300
    CACHE_TTL_GRADES: int = 30

    SECRET_KEY: str = "sandbox-default-secret-key-12345"
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_MINUTES: int = 60
    COOKIE_SECURE: bool = False

    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str

    @property
    def database_url(self) -> str:
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}" f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(
        env_file=target_env_file,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

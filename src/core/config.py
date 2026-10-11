from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Pydantic автоматично прочитає ці значення з файлу .env
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str

    SECRET_KEY: str = "change-me-in-env"
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_MINUTES: int = 60
    COOKIE_SECURE: bool = False
    ADMIN_EMAIL: str = "admin@school.ua"
    ADMIN_PASSWORD: str = "Admin12345"

    # Ця властивість динамічно збирає URL з підтягнутих вище змінних
    @property
    def database_url(self) -> str:
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

# class reads from .env file locally; real env vars (Lambda) take priority

from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # injected by Terraform in LocalStack/AWS, read from .env when running fastapi dev
    is_local: bool = False
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_name: str = "postgres"
    postgres_user: str = "postgres"
    postgres_pass: str = ""

    secret_key: str
    cors_origins: list[str] = ["http://localhost:3000"]
    frontend_origin: str = "http://localhost:3000"
    access_token_expire_minutes: int = 30
    # refresh_token_expire_days: int = 7

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    @computed_field
    @property
    def database_url(self) -> str:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_pass or None,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_name,
        ).render_as_string(hide_password=False)


settings = Settings()
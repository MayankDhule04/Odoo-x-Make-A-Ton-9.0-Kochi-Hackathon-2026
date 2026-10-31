"""Application settings, read from environment variables."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

# Used only when APP_ENV is "development" and JWT_SECRET is unset, so a fresh clone
# runs with one command. Any other environment must set its own secret.
DEV_JWT_SECRET = "dev-only-insecure-jwt-secret-do-not-use-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    app_env: str = "development"
    # docker-compose.yml sets DATABASE_URL for the container. This default is for
    # running the API directly on your machine against the Postgres container.
    database_url: str = "postgresql+psycopg://brightloop:brightloop@localhost:5433/brightloop"
    # When unset, tests use the main database name plus "_test" on the same server.
    test_database_url: str | None = None

    jwt_secret: str = ""
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7

    @model_validator(mode="after")
    def _check_jwt_secret(self) -> "Settings":
        if not self.jwt_secret:
            if self.app_env != "development":
                raise ValueError("JWT_SECRET must be set when APP_ENV is not 'development'.")
            self.jwt_secret = DEV_JWT_SECRET
        elif len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long.")
        return self

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    def resolved_test_database_url(self) -> str:
        if self.test_database_url:
            return self.test_database_url
        url = make_url(self.database_url)
        return url.set(database=f"{url.database}_test").render_as_string(hide_password=False)


settings = Settings()

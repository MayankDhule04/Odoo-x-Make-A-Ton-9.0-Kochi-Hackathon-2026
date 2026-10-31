"""Application settings, read from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    app_env: str = "development"
    # docker-compose.yml sets DATABASE_URL for the container. This default is for
    # running the API directly on your machine against the Postgres container.
    database_url: str = "postgresql+psycopg://brightloop:brightloop@localhost:5433/brightloop"
    # When unset, tests use the main database name plus "_test" on the same server.
    test_database_url: str | None = None

    def resolved_test_database_url(self) -> str:
        if self.test_database_url:
            return self.test_database_url
        url = make_url(self.database_url)
        return url.set(database=f"{url.database}_test").render_as_string(hide_password=False)


settings = Settings()

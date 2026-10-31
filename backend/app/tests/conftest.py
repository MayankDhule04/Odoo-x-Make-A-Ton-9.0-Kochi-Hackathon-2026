"""Shared pytest fixtures.

Tests run against a separate database: the main database name plus "_test". It is
dropped and rebuilt from the Alembic migrations at the start of every run, and each
test runs inside a transaction that is rolled back afterwards.
"""

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import create_db_engine, get_db
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _recreate_database(url: URL) -> None:
    name = url.database or ""
    # Safety net: never drop anything that isn't clearly a test database.
    if not re.fullmatch(r"[A-Za-z0-9_]+_test", name):
        raise RuntimeError(
            f"Refusing to recreate database {name!r}: test database names must end with '_test'."
        )
    admin_engine = create_db_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
            connection.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session")
def test_db_url() -> URL:
    return make_url(settings.resolved_test_database_url())


@pytest.fixture(scope="session")
def alembic_cfg(test_db_url: URL) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    # ConfigParser treats "%" as interpolation syntax, so escape it.
    rendered_url = test_db_url.render_as_string(hide_password=False).replace("%", "%%")
    config.set_main_option("sqlalchemy.url", rendered_url)
    return config


@pytest.fixture(scope="session")
def engine(test_db_url: URL, alembic_cfg: Config) -> Iterator[Engine]:
    _recreate_database(test_db_url)
    command.upgrade(alembic_cfg, "head")
    test_engine = create_db_engine(test_db_url)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    """A session whose changes are rolled back after the test, even if the code under
    test calls commit()."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """API client whose requests use the rolled-back test session."""

    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)

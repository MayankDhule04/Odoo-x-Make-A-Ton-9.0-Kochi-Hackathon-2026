"""Shared pytest fixtures.

Tests run against a separate database: the main database name plus "_test". It is
dropped and rebuilt from the Alembic migrations at the start of every run, and each
test runs inside a transaction that is rolled back afterwards.
"""

import itertools
import re
from collections.abc import Callable, Iterator
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
from app.models.auth import User, UserRole
from app.services.auth import create_user
from app.tests.helpers import TEST_PASSWORD, auth_headers

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
    """Anonymous API client whose requests use the rolled-back test session."""

    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


# --- Users and logged-in clients, for every domain's tests ------------------------------


@pytest.fixture
def make_user(db_session: Session) -> Callable[..., User]:
    """Factory: make_user(UserRole.STAFF), make_user(email="a@example.com"), ...

    CUSTOMER users also get their customer record. Every user's password is TEST_PASSWORD
    unless you pass another one.
    """
    counter = itertools.count(1)

    def _make_user(
        role: UserRole = UserRole.CUSTOMER,
        *,
        email: str | None = None,
        password: str = TEST_PASSWORD,
        full_name: str | None = None,
    ) -> User:
        number = next(counter)
        return create_user(
            db_session,
            email=email or f"{role.value.lower()}{number}@example.com",
            password=password,
            full_name=full_name or f"Test {role.value.title()} {number}",
            role=role,
        )

    return _make_user


@pytest.fixture
def admin_user(make_user: Callable[..., User]) -> User:
    return make_user(UserRole.ADMIN)


@pytest.fixture
def staff_user(make_user: Callable[..., User]) -> User:
    return make_user(UserRole.STAFF)


@pytest.fixture
def customer_user(make_user: Callable[..., User]) -> User:
    return make_user(UserRole.CUSTOMER)


@pytest.fixture
def client_as(client: TestClient) -> Iterator[Callable[[User], TestClient]]:
    """Factory: client_as(user) returns an API client logged in as that user."""
    opened: list[TestClient] = []

    def _client_as(user: User) -> TestClient:
        logged_in = TestClient(app, headers=auth_headers(user))
        opened.append(logged_in)
        return logged_in

    yield _client_as
    for logged_in in opened:
        logged_in.close()


@pytest.fixture
def admin_client(client_as: Callable[[User], TestClient], admin_user: User) -> TestClient:
    return client_as(admin_user)


@pytest.fixture
def staff_client(client_as: Callable[[User], TestClient], staff_user: User) -> TestClient:
    return client_as(staff_user)


@pytest.fixture
def customer_client(client_as: Callable[[User], TestClient], customer_user: User) -> TestClient:
    return client_as(customer_user)

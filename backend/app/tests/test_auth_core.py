"""Accounts, the password policy, login, tokens, require_role and customer scoping."""

from collections.abc import Callable, Iterator
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import DbSession, get_db
from app.core.rbac import AdminUser, CurrentCustomer, CurrentPrincipal, CurrentUser, StaffOrAdmin
from app.core.security import (
    JWT_ALGORITHM,
    create_refresh_token,
    password_policy_errors,
    verify_password,
)
from app.models.auth import User, UserRole
from app.models.customers import Customer
from app.seed.demo_users import DEMO_USERS, seed_demo_users
from app.services.auth import EmailAlreadyRegisteredError, PasswordPolicyError, create_user
from app.tests.helpers import TEST_PASSWORD, auth_headers

# --- Password policy ----------------------------------------------------------------


def test_password_with_exactly_8_characters_is_rejected() -> None:
    assert password_policy_errors("Abcdef!1") == ["Use at least 9 characters."]


def test_valid_password_with_9_characters_is_accepted() -> None:
    assert password_policy_errors("Abcdefg!1") == []


@pytest.mark.parametrize(
    ("password", "expected_error"),
    [
        ("abcdefgh!1", "Add at least one uppercase letter."),
        ("ABCDEFGH!1", "Add at least one lowercase letter."),
        ("Abcdefgh12", "Add at least one special character, such as ! @ # or $."),
    ],
)
def test_password_missing_a_character_class_is_rejected(password: str, expected_error: str) -> None:
    assert password_policy_errors(password) == [expected_error]


def test_create_user_enforces_the_password_policy(db_session: Session) -> None:
    with pytest.raises(PasswordPolicyError):
        create_user(db_session, email="weak@example.com", password="Abcdef!1", full_name="Weak", role=UserRole.CUSTOMER)


# --- Accounts -----------------------------------------------------------------------


def test_duplicate_email_is_rejected_regardless_of_case(make_user: Callable[..., User]) -> None:
    make_user(email="ana@example.com")

    with pytest.raises(EmailAlreadyRegisteredError):
        make_user(email="ANA@Example.COM")


def test_database_itself_rejects_emails_that_differ_only_in_case(db_session: Session) -> None:
    db_session.add(User(email="Raj@example.com", password_hash="x", full_name="Raj", role=UserRole.STAFF))
    db_session.flush()

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(User(email="raj@EXAMPLE.com", password_hash="x", full_name="Raj 2", role=UserRole.STAFF))
            db_session.flush()


def test_password_is_stored_as_an_argon2_hash(customer_user: User) -> None:
    assert customer_user.password_hash.startswith("$argon2")
    assert verify_password(customer_user.password_hash, TEST_PASSWORD)


def test_customer_user_gets_a_linked_customer_record(db_session: Session, customer_user: User) -> None:
    customer = db_session.scalar(select(Customer).where(Customer.user_id == customer_user.id))

    assert customer is not None
    assert customer.email == customer_user.email


def test_staff_and_admin_users_get_no_customer_record(
    db_session: Session, staff_user: User, admin_user: User
) -> None:
    linked = db_session.scalars(select(Customer).where(Customer.user_id.in_([staff_user.id, admin_user.id]))).all()

    assert linked == []


# --- Login and tokens ---------------------------------------------------------------


def test_login_returns_an_access_token_and_sets_an_httponly_refresh_cookie(
    client: TestClient, staff_user: User
) -> None:
    response = client.post("/api/auth/login", json={"email": staff_user.email.upper(), "password": TEST_PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"] == {
        "id": staff_user.id,
        "email": staff_user.email,
        "full_name": staff_user.full_name,
        "role": "STAFF",
    }
    cookie_header = response.headers["set-cookie"]
    assert "brightloop_refresh=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Path=/api/auth" in cookie_header

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["id"] == staff_user.id


def test_wrong_password_and_unknown_email_get_the_same_answer(client: TestClient, staff_user: User) -> None:
    wrong_password = client.post("/api/auth/login", json={"email": staff_user.email, "password": "Wrong@Pass123"})
    unknown_email = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": TEST_PASSWORD})

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_deactivated_user_cannot_log_in(client: TestClient, db_session: Session, staff_user: User) -> None:
    staff_user.is_active = False
    db_session.flush()

    response = client.post("/api/auth/login", json={"email": staff_user.email, "password": TEST_PASSWORD})

    assert response.status_code == 401


def test_protected_route_without_a_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_refresh_token_is_not_accepted_as_an_access_token(client: TestClient, staff_user: User) -> None:
    refresh = create_refresh_token(user_id=staff_user.id, token_version=staff_user.token_version).token

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {refresh}"})

    assert response.status_code == 401


def test_expired_access_token_is_rejected(client: TestClient, staff_user: User) -> None:
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    expired = jwt.encode(
        {"sub": str(staff_user.id), "ver": 0, "type": "access", "iat": past, "exp": past + timedelta(minutes=1)},
        settings.jwt_secret,
        algorithm=JWT_ALGORITHM,
    )

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401


def test_token_signed_with_another_secret_is_rejected(client: TestClient, staff_user: User) -> None:
    now = datetime.now(timezone.utc)
    forged = jwt.encode(
        {"sub": str(staff_user.id), "ver": 0, "type": "access", "iat": now, "exp": now + timedelta(minutes=5)},
        "an-attacker-chosen-secret-that-is-32-characters-plus",
        algorithm=JWT_ALGORITHM,
    )

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"})

    assert response.status_code == 401


def test_bumping_token_version_revokes_existing_tokens(
    client: TestClient, db_session: Session, staff_user: User
) -> None:
    headers = auth_headers(staff_user)
    staff_user.token_version += 1
    db_session.flush()

    response = client.get("/api/auth/me", headers=headers)

    assert response.status_code == 401


# --- require_role and customer scoping ----------------------------------------------


@pytest.fixture
def rbac_client(db_session: Session) -> Iterator[Callable[[User | None], TestClient]]:
    """A throwaway app with one route per RBAC dependency, to test them in isolation."""
    probe = FastAPI()

    @probe.get("/admin")
    def admin_only(user: AdminUser) -> dict[str, str]:
        return {"role": user.role.value}

    @probe.get("/staff")
    def staff_or_admin(user: StaffOrAdmin) -> dict[str, str]:
        return {"role": user.role.value}

    @probe.get("/any")
    def any_role(user: CurrentUser) -> dict[str, str]:
        return {"role": user.role.value}

    @probe.get("/customer")
    def customer_only(customer: CurrentCustomer) -> dict[str, int]:
        return {"customer_id": customer.id}

    @probe.get("/customers")
    def visible_customers(db: DbSession, principal: CurrentPrincipal) -> list[int]:
        # On the customers table itself, the owning customer's id is the primary key.
        statement = principal.scope(select(Customer.id).order_by(Customer.id), Customer.id)
        return list(db.scalars(statement))

    def override_get_db() -> Iterator[Session]:
        yield db_session

    probe.dependency_overrides[get_db] = override_get_db

    def _client(user: User | None) -> TestClient:
        return TestClient(probe, headers=auth_headers(user) if user else {})

    yield _client


@pytest.mark.parametrize(
    ("path", "allowed_roles"),
    [
        ("/admin", {UserRole.ADMIN}),
        ("/staff", {UserRole.ADMIN, UserRole.STAFF}),
        ("/any", {UserRole.ADMIN, UserRole.STAFF, UserRole.CUSTOMER}),
        ("/customer", {UserRole.CUSTOMER}),
    ],
)
def test_each_role_against_each_rbac_dependency(
    rbac_client: Callable[[User | None], TestClient],
    make_user: Callable[..., User],
    path: str,
    allowed_roles: set[UserRole],
) -> None:
    assert rbac_client(None).get(path).status_code == 401

    for role in UserRole:
        status_code = rbac_client(make_user(role)).get(path).status_code
        expected = 200 if role in allowed_roles else 403
        assert status_code == expected, f"{role.value} on {path}: got {status_code}, expected {expected}"


def test_customers_see_only_their_own_rows_and_staff_see_all(
    rbac_client: Callable[[User | None], TestClient],
    db_session: Session,
    make_user: Callable[..., User],
) -> None:
    alice, bob = make_user(UserRole.CUSTOMER), make_user(UserRole.CUSTOMER)
    staff = make_user(UserRole.STAFF)
    alice_id = db_session.scalar(select(Customer.id).where(Customer.user_id == alice.id))
    bob_id = db_session.scalar(select(Customer.id).where(Customer.user_id == bob.id))

    assert rbac_client(alice).get("/customers").json() == [alice_id]
    assert rbac_client(bob).get("/customers").json() == [bob_id]
    assert {alice_id, bob_id} <= set(rbac_client(staff).get("/customers").json())


# --- Demo users ---------------------------------------------------------------------


def test_seeding_demo_users_is_idempotent_and_they_can_log_in(client: TestClient, db_session: Session) -> None:
    first = seed_demo_users(db_session)
    second = seed_demo_users(db_session)

    assert sorted(first) == sorted(demo.email for demo in DEMO_USERS)
    assert second == []
    for demo in DEMO_USERS:
        response = client.post("/api/auth/login", json={"email": demo.email, "password": demo.password})
        assert response.status_code == 200, demo.email
        assert response.json()["user"]["role"] == demo.role.value

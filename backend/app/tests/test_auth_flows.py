"""Tests for the auth flows added in step 4: signup, refresh, password reset,
rate limiting, create-staff, and customer CRUD."""

import time
from collections.abc import Callable
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rate_limit import _buckets
from app.models.auth import PasswordResetToken, User, UserRole
from app.models.customers import Customer
from app.tests.helpers import TEST_PASSWORD, auth_headers


@pytest.fixture(autouse=True)
def _clear_rate_limit_buckets() -> None:
    """Reset rate-limit counters between tests so one test can't block another."""
    _buckets.clear()

# --- Signup -------------------------------------------------------------------------


def test_signup_creates_a_customer_and_returns_tokens(client: TestClient) -> None:
    response = client.post("/api/auth/signup", json={
        "email": "new@example.com",
        "password": "NewUser@123",
        "full_name": "New User",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "CUSTOMER"
    assert body["user"]["email"] == "new@example.com"
    assert body["access_token"]
    assert "brightloop_refresh" in response.headers.get("set-cookie", "")


def test_signup_rejects_weak_password(client: TestClient) -> None:
    response = client.post("/api/auth/signup", json={
        "email": "weak@example.com",
        "password": "short",
        "full_name": "Weak",
    })
    assert response.status_code == 422


def test_signup_rejects_duplicate_email(client: TestClient, customer_user: User) -> None:
    response = client.post("/api/auth/signup", json={
        "email": customer_user.email,
        "password": "Duplicate@123",
        "full_name": "Dup",
    })
    assert response.status_code == 409


# --- Token refresh ------------------------------------------------------------------


def test_refresh_returns_a_new_token_pair(client: TestClient, staff_user: User) -> None:
    # First login to get the cookie.
    login_response = client.post("/api/auth/login", json={"email": staff_user.email, "password": TEST_PASSWORD})
    assert login_response.status_code == 200

    # The TestClient carries cookies automatically.
    refresh_response = client.post("/api/auth/refresh")
    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]


def test_refresh_without_cookie_returns_401(client: TestClient) -> None:
    response = client.post("/api/auth/refresh")
    assert response.status_code == 401


# --- Password reset -----------------------------------------------------------------


def test_forgot_password_always_returns_success(client: TestClient) -> None:
    # Unknown email: same response.
    response = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert response.status_code == 200
    assert "reset link" in response.json()["message"].lower()


def test_full_reset_flow(client: TestClient, db_session: Session, customer_user: User) -> None:
    # Request a reset.
    client.post("/api/auth/forgot-password", json={"email": customer_user.email})

    # Find the raw token from the outbox (it's in the email body).
    from app.models.auth.email_outbox import EmailOutbox
    outbox = db_session.scalar(select(EmailOutbox).where(EmailOutbox.to_email == customer_user.email))
    assert outbox is not None
    # Extract the token from the link: ...?token=<TOKEN>
    import re
    match = re.search(r"token=([A-Za-z0-9_-]+)", outbox.body)
    assert match
    raw_token = match.group(1)

    # Reset the password.
    new_password = "NewPass@456"
    response = client.post("/api/auth/reset-password", json={"token": raw_token, "new_password": new_password})
    assert response.status_code == 200

    # Login with the new password.
    login_response = client.post("/api/auth/login", json={"email": customer_user.email, "password": new_password})
    assert login_response.status_code == 200

    # Old password no longer works.
    old_login = client.post("/api/auth/login", json={"email": customer_user.email, "password": TEST_PASSWORD})
    assert old_login.status_code == 401


def test_reset_token_is_single_use(client: TestClient, db_session: Session, make_user: Callable[..., User]) -> None:
    user = make_user(UserRole.CUSTOMER, email="single-use-test@example.com")
    client.post("/api/auth/forgot-password", json={"email": user.email})

    from app.models.auth.email_outbox import EmailOutbox
    import re
    outbox = db_session.scalar(
        select(EmailOutbox).where(EmailOutbox.to_email == user.email).order_by(EmailOutbox.id.desc())
    )
    assert outbox is not None
    raw_token = re.search(r"token=([A-Za-z0-9_-]+)", outbox.body).group(1)

    # First use: succeeds.
    assert client.post("/api/auth/reset-password", json={"token": raw_token, "new_password": "First@Use99"}).status_code == 200
    # Second use: fails.
    assert client.post("/api/auth/reset-password", json={"token": raw_token, "new_password": "Second@Use99"}).status_code == 400


def test_expired_reset_token_is_rejected(client: TestClient, db_session: Session, make_user: Callable[..., User]) -> None:
    from datetime import datetime, timedelta, timezone
    user = make_user(UserRole.CUSTOMER, email="expired-test@example.com")
    client.post("/api/auth/forgot-password", json={"email": user.email})

    # Move the expiry into the past.
    token_row = db_session.scalar(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user.id).order_by(PasswordResetToken.id.desc())
    )
    assert token_row is not None
    token_row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.flush()

    import re
    from app.models.auth.email_outbox import EmailOutbox
    outbox = db_session.scalar(
        select(EmailOutbox).where(EmailOutbox.to_email == user.email).order_by(EmailOutbox.id.desc())
    )
    raw_token = re.search(r"token=([A-Za-z0-9_-]+)", outbox.body).group(1)

    response = client.post("/api/auth/reset-password", json={"token": raw_token, "new_password": "Expired@123"})
    assert response.status_code == 400


# --- Rate limiting ------------------------------------------------------------------


def test_login_rate_limit_fires(client: TestClient) -> None:
    _buckets.clear()
    # Exceed the 10-per-minute limit.
    for _ in range(10):
        client.post("/api/auth/login", json={"email": "rl@example.com", "password": "x"})
    response = client.post("/api/auth/login", json={"email": "rl@example.com", "password": "x"})
    assert response.status_code == 429
    _buckets.clear()


# --- Create staff (admin only) ------------------------------------------------------


def test_admin_can_create_staff(client: TestClient, admin_user: User) -> None:
    response = client.post("/api/auth/staff", json={
        "email": "newstaff@example.com",
        "password": "Staff@Pass1",
        "full_name": "New Staff",
    }, headers=auth_headers(admin_user))
    assert response.status_code == 201
    assert response.json()["role"] == "STAFF"


def test_staff_cannot_create_staff(client: TestClient, staff_user: User) -> None:
    response = client.post("/api/auth/staff", json={
        "email": "x@example.com",
        "password": "Staff@Pass1",
        "full_name": "X",
    }, headers=auth_headers(staff_user))
    assert response.status_code == 403


# --- Customer CRUD ------------------------------------------------------------------


def test_staff_can_list_and_create_customers(client: TestClient, staff_user: User) -> None:
    headers = auth_headers(staff_user)

    # Create a customer.
    create_response = client.post("/api/customers", json={
        "name": "Acme Corp",
        "email": "acme@example.com",
    }, headers=headers)
    assert create_response.status_code == 201
    assert create_response.json()["name"] == "Acme Corp"

    # List customers.
    list_response = client.get("/api/customers", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] >= 1


def test_customer_can_only_see_own_profile(
    client: TestClient,
    customer_user: User,
    make_user: Callable[..., User],
    db_session: Session,
) -> None:
    other = make_user(UserRole.CUSTOMER)
    other_customer = db_session.scalar(select(Customer).where(Customer.user_id == other.id))

    headers = auth_headers(customer_user)

    # Own profile works.
    my_response = client.get("/api/customers/me", headers=headers)
    assert my_response.status_code == 200

    # Trying to access another customer by ID fails.
    other_response = client.get(f"/api/customers/{other_customer.id}", headers=headers)
    assert other_response.status_code == 403  # not staff or admin


def test_password_policy_endpoint_returns_rules(client: TestClient) -> None:
    response = client.get("/api/auth/password-policy")
    assert response.status_code == 200
    body = response.json()
    assert body["min_length"] == 9
    assert body["requires_uppercase"] is True

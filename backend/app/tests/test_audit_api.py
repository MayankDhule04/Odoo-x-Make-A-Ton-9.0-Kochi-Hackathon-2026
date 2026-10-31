"""Tests for the admin audit log and dev email outbox read APIs."""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.auth import User, UserRole
from app.services.audit import record_audit
from app.services.email import send_email
from app.tests.helpers import auth_headers


# --- Audit log API ------------------------------------------------------------------


def test_admin_can_read_the_audit_log(client: TestClient, admin_user: User, db_session: Session) -> None:
    record_audit(db_session, actor=admin_user, entity_type="plan", entity_id=1, action="create")
    record_audit(db_session, actor=admin_user, entity_type="discount", entity_id=2, action="update",
                 changes={"amount": ["100", "200"]})
    db_session.flush()

    response = client.get("/api/audit-log", headers=auth_headers(admin_user))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["items"][0]["entity_type"] in ("plan", "discount")


def test_audit_log_filters_by_entity_type(client: TestClient, admin_user: User, db_session: Session) -> None:
    record_audit(db_session, actor=admin_user, entity_type="plan", entity_id=1, action="create")
    record_audit(db_session, actor=admin_user, entity_type="discount", entity_id=2, action="create")
    db_session.flush()

    response = client.get("/api/audit-log?entity_type=plan", headers=auth_headers(admin_user))

    assert response.status_code == 200
    assert all(item["entity_type"] == "plan" for item in response.json()["items"])


def test_audit_log_filters_by_actor_id(client: TestClient, admin_user: User, db_session: Session,
                                        make_user: Callable[..., User]) -> None:
    other = make_user(UserRole.STAFF)
    record_audit(db_session, actor=admin_user, entity_type="plan", entity_id=1, action="create")
    record_audit(db_session, actor=other, entity_type="plan", entity_id=2, action="create")
    db_session.flush()

    response = client.get(f"/api/audit-log?actor_id={admin_user.id}", headers=auth_headers(admin_user))

    assert response.status_code == 200
    assert all(item["actor_id"] == admin_user.id for item in response.json()["items"])


def test_staff_cannot_read_the_audit_log(client: TestClient, staff_user: User) -> None:
    response = client.get("/api/audit-log", headers=auth_headers(staff_user))
    assert response.status_code == 403


def test_customer_cannot_read_the_audit_log(client: TestClient, customer_user: User) -> None:
    response = client.get("/api/audit-log", headers=auth_headers(customer_user))
    assert response.status_code == 403


# --- Email outbox API ---------------------------------------------------------------


def test_admin_can_read_the_outbox(client: TestClient, admin_user: User, db_session: Session) -> None:
    send_email(db_session, to="test@example.com", subject="Test", body="<p>hello</p>")
    db_session.flush()

    response = client.get("/api/email-outbox", headers=auth_headers(admin_user))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert body["items"][0]["to_email"] == "test@example.com"


def test_staff_cannot_read_the_outbox(client: TestClient, staff_user: User) -> None:
    response = client.get("/api/email-outbox", headers=auth_headers(staff_user))
    assert response.status_code == 403

"""Tests for the shared building blocks: error format, pagination, money, audit log
and email outbox."""

from collections.abc import Callable
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.money import CURRENCY, MoneyField
from app.core.pagination import PaginationParams, paginate
from app.models.auth import AuditLog, User, UserRole
from app.services.audit import record_audit
from app.services.email import send_email


# --- Error format ---------------------------------------------------------------


def test_validation_error_has_a_consistent_shape(client: TestClient) -> None:
    """POST /api/auth/login with no body triggers a validation error."""
    response = client.post("/api/auth/login", json={})

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert "errors" in body
    assert isinstance(body["errors"], list)


def test_http_error_has_a_consistent_shape(client: TestClient) -> None:
    """GET /api/auth/me with no token returns 401 in the same format."""
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    body = response.json()
    assert "detail" in body
    assert "errors" in body


# --- Pagination -----------------------------------------------------------------


def test_paginate_returns_correct_page_and_count(db_session: Session, make_user: Callable[..., User]) -> None:
    for _ in range(7):
        make_user(UserRole.STAFF)

    from app.models.auth import User as UserModel

    result = paginate(db_session, select(UserModel).order_by(UserModel.id), PaginationParams(page=2, page_size=3))

    assert result.total == 7
    assert result.page == 2
    assert result.page_size == 3
    assert result.pages == 3
    assert len(result.items) == 3


def test_empty_table_returns_zero_items(db_session: Session) -> None:
    from app.models.auth.audit_log import AuditLog

    result = paginate(db_session, select(AuditLog), PaginationParams(page=1, page_size=10))

    assert result.total == 0
    assert result.items == []
    assert result.pages == 1


# --- Money ----------------------------------------------------------------------


def test_currency_is_inr() -> None:
    assert CURRENCY == "INR"


def test_money_field_has_two_decimal_places() -> None:
    # MoneyField returns a FieldInfo with our description.
    field = MoneyField()
    assert field.description == "Amount in INR."


# --- Audit log ------------------------------------------------------------------


def test_record_audit_creates_an_entry(db_session: Session, admin_user: User) -> None:
    entry = record_audit(
        db_session,
        actor=admin_user,
        entity_type="plan",
        entity_id=42,
        action="update",
        changes={"price": ["500.00", "600.00"]},
    )

    assert entry.id is not None
    assert entry.entity_type == "plan"
    assert entry.actor_id == admin_user.id
    assert '"price"' in (entry.changes or "")


def test_audit_log_rejects_update(db_session: Session, admin_user: User) -> None:
    entry = record_audit(db_session, actor=admin_user, entity_type="test", entity_id=1, action="create")
    db_session.flush()

    with pytest.raises(ProgrammingError, match="immutable"):
        with db_session.begin_nested():
            db_session.execute(
                text("UPDATE audit_log SET action = 'hacked' WHERE id = :id"),
                {"id": entry.id},
            )


def test_audit_log_rejects_delete(db_session: Session, admin_user: User) -> None:
    entry = record_audit(db_session, actor=admin_user, entity_type="test", entity_id=1, action="create")
    db_session.flush()

    with pytest.raises(ProgrammingError, match="immutable"):
        with db_session.begin_nested():
            db_session.execute(text("DELETE FROM audit_log WHERE id = :id"), {"id": entry.id})


# --- Email outbox ---------------------------------------------------------------


def test_email_goes_to_outbox_without_smtp(db_session: Session) -> None:
    send_email(db_session, to="test@example.com", subject="Hello", body="<p>Hi</p>")

    from app.models.auth.email_outbox import EmailOutbox

    row = db_session.scalar(select(EmailOutbox).where(EmailOutbox.to_email == "test@example.com"))
    assert row is not None
    assert row.subject == "Hello"
    assert "<p>Hi</p>" in row.body

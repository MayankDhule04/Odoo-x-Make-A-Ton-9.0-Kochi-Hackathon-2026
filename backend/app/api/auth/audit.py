"""Admin-only read API for the immutable audit log and the dev email outbox.

The audit log records who changed prices, plans, discounts and record states.
The outbox shows emails sent in development (password resets, invoices, dunning).
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.config import settings
from app.core.db import DbSession
from app.core.pagination import Page, PaginationDep, paginate
from app.core.rbac import AdminUser
from app.models.auth.audit_log import AuditLog
from app.models.auth.email_outbox import EmailOutbox
from app.schemas.auth.audit import AuditLogRead, EmailOutboxRead

router = APIRouter(tags=["audit"])


@router.get("/audit-log", response_model=Page[AuditLogRead])
def list_audit_log(
    db: DbSession,
    params: PaginationDep,
    _admin: AdminUser,
    entity_type: str | None = Query(default=None, description='Filter by entity, e.g. "plan" or "subscription".'),
    actor_id: int | None = Query(default=None, description="Filter by the user who made the change."),
    after: datetime | None = Query(default=None, description="Only entries created after this UTC timestamp."),
    before: datetime | None = Query(default=None, description="Only entries created before this UTC timestamp."),
) -> Page[AuditLogRead]:
    query = select(AuditLog).order_by(AuditLog.id.desc())
    if entity_type is not None:
        query = query.where(AuditLog.entity_type == entity_type)
    if actor_id is not None:
        query = query.where(AuditLog.actor_id == actor_id)
    if after is not None:
        query = query.where(AuditLog.created_at >= after)
    if before is not None:
        query = query.where(AuditLog.created_at <= before)
    return paginate(db, query, params)


@router.get("/email-outbox", response_model=Page[EmailOutboxRead])
def list_outbox(
    db: DbSession,
    params: PaginationDep,
    _admin: AdminUser,
) -> Page[EmailOutboxRead]:
    """Dev-only screen showing emails that were written to the outbox instead of sent
    via SMTP. Hidden when SMTP is configured (there's nothing to show)."""
    if not settings.is_development:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not available outside development.")
    query = select(EmailOutbox).order_by(EmailOutbox.id.desc())
    return paginate(db, query, params)

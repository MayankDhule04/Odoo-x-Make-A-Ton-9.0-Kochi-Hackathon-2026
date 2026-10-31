"""Schemas for the audit log and dev email outbox read APIs."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None
    entity_type: str
    entity_id: int
    action: str
    changes: str | None
    created_at: datetime


class EmailOutboxRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    to_email: str
    subject: str
    body: str
    created_at: datetime

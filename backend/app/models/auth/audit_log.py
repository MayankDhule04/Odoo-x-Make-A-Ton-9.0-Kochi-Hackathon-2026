"""Immutable audit log: who changed what, when, and what the change was.

The database enforces immutability: the migration adds a trigger that rejects
UPDATE and DELETE on the audit_log table.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    """One row per recorded change.  Never updated or deleted."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Who made the change (nullable for system-generated entries like scheduled jobs).
    actor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL")
    )
    # What was changed: e.g. "plan", "discount", "subscription", "invoice".
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # The action: "create", "update", "delete", "transition", ...
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # Free-form JSON or text describing what changed.
    changes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

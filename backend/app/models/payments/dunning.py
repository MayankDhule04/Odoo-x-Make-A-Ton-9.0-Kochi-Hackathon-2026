"""Dunning attempts: the log of reminders sent and suspensions applied for overdue invoices."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DunningKind(str, enum.Enum):
    REMINDER = "REMINDER"
    SUSPENSION = "SUSPENSION"


class DunningAttempt(Base):
    """One row per dunning action taken against an overdue invoice."""

    __tablename__ = "dunning_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Which step in the retry schedule this is (1..N); 0 for a manual reminder.
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    kind: Mapped[DunningKind] = mapped_column(
        Enum(DunningKind, native_enum=False, create_constraint=True, name="dunning_kind", length=20),
        nullable=False,
    )
    days_overdue: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    invoice = relationship("Invoice")

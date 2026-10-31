"""Proration adjustments produced by a mid-cycle plan/quantity change.

Each change writes a credit (unused part of the current period) and/or a charge (the new
configuration for the remaining period). Billing (Member 3) can pick up unapplied rows and
add them to the subscription's next invoice, then mark them applied with the invoice id.
"""

from datetime import datetime

from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.money import MoneyColumn
from app.models.base import Base


class ProrationAdjustment(Base):
    """A signed money adjustment: negative = credit to the customer, positive = extra charge."""

    __tablename__ = "proration_adjustments"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    # Signed amount: credits are negative, charges positive.
    amount: Mapped[Decimal] = MoneyColumn(nullable=False)
    applied: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false(), index=True
    )
    # Set by billing when the adjustment lands on an invoice (no FK to keep domains decoupled).
    invoice_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    subscription = relationship("Subscription")

"""Subscription state-transition history: who moved it from which state to which, when."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.subscriptions.subscription import Subscription, SubscriptionStatus


class SubscriptionHistory(Base):
    """One row per transition, shown as a timeline in the UI."""

    __tablename__ = "subscription_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # from_status is null for the initial creation row.
    from_status: Mapped[SubscriptionStatus | None] = mapped_column(
        Enum(SubscriptionStatus, native_enum=False, create_constraint=True,
             name="sub_history_from_status", length=20),
        nullable=True,
    )
    to_status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, native_enum=False, create_constraint=True,
             name="sub_history_to_status", length=20),
        nullable=False,
    )
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    subscription: Mapped["Subscription"] = relationship(back_populates="history")

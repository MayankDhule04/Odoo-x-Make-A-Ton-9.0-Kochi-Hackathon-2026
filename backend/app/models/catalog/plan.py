"""Subscription plans: price, billing period, availability window and per-plan flags."""

import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, Enum, Integer, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.money import MoneyColumn
from app.models.base import Base, TimestampMixin


class BillingPeriod(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class Plan(TimestampMixin, Base):
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("price >= 0", name="price_non_negative"),
        CheckConstraint("min_quantity >= 1", name="min_quantity_positive"),
        CheckConstraint("available_to >= available_from", name="dates_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    price: Mapped[Decimal] = MoneyColumn(nullable=False)
    billing_period: Mapped[BillingPeriod] = mapped_column(
        Enum(BillingPeriod, native_enum=False, create_constraint=True, name="billing_period", length=20),
        nullable=False,
    )
    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    available_from: Mapped[date] = mapped_column(Date, nullable=False)
    available_to: Mapped[date] = mapped_column(Date, nullable=False)

    # Per-plan flags set by the admin.
    auto_close: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    allow_early_close: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    allow_pause: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    allow_renew: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())

    def is_available_on(self, on: date) -> bool:
        """A plan can only be used for new subscriptions inside its window."""
        return self.available_from <= on <= self.available_to

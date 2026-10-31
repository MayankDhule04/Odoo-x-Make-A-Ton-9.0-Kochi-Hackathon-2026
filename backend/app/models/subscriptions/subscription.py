"""Subscriptions and their lines.

State machine: DRAFT -> QUOTATION -> CONFIRMED -> ACTIVE -> (PAUSED) -> CLOSED.
Transitions go through app.services.subscriptions.transitions, which rejects illegal
moves and writes a history row + audit entry.
"""

import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.money import MoneyColumn
from app.models.base import Base, TimestampMixin

ZERO = Decimal("0.00")


class SubscriptionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    QUOTATION = "QUOTATION"
    CONFIRMED = "CONFIRMED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class PaymentTerms(str, enum.Enum):
    IMMEDIATE = "IMMEDIATE"
    NET_15 = "NET_15"
    NET_30 = "NET_30"


def status_column(constraint_name: str, **kwargs):
    return mapped_column(
        Enum(
            SubscriptionStatus,
            native_enum=False,
            create_constraint=True,
            name=constraint_name,
            length=20,
        ),
        **kwargs,
    )


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("expiry_date >= start_date", name="dates_valid"),
        # Billing (Member 3) scans due subscriptions by this composite index.
        Index("ix_subscriptions_status_next_billing_date", "status", "next_billing_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Auto-generated, e.g. SUB-2026-000123.
    number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Set when the subscription becomes ACTIVE; billing advances it.
    next_billing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_terms: Mapped[PaymentTerms] = mapped_column(
        Enum(PaymentTerms, native_enum=False, create_constraint=True, name="payment_terms", length=20),
        nullable=False,
        default=PaymentTerms.IMMEDIATE,
    )
    status: Mapped[SubscriptionStatus] = status_column(
        "subscription_status", nullable=False, default=SubscriptionStatus.DRAFT
    )

    lines: Mapped[list["SubscriptionLine"]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan", order_by="SubscriptionLine.id"
    )
    history: Mapped[list["SubscriptionHistory"]] = relationship(
        back_populates="subscription",
        cascade="all, delete-orphan",
        order_by="SubscriptionHistory.id",
    )

    @hybrid_property
    def amount_total(self) -> Decimal:
        """Sum of line amounts (pre-tax)."""
        return sum((line.amount for line in self.lines), ZERO)


class SubscriptionLine(Base):
    __tablename__ = "subscription_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    tax_id: Mapped[int | None] = mapped_column(
        ForeignKey("taxes.id", ondelete="SET NULL"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    unit_price: Mapped[Decimal] = MoneyColumn(nullable=False)
    amount: Mapped[Decimal] = MoneyColumn(nullable=False)  # quantity * unit_price (pre-tax)

    subscription: Mapped["Subscription"] = relationship(back_populates="lines")

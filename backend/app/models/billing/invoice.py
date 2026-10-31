"""Invoice models and status.

State machine: DRAFT -> CONFIRMED -> PAID, plus CANCELLED.
Confirmed invoices are immutable; corrections happen through cancellation and re-issuance.
Numbering: INV-<year>-<zero-padded id>, sequential without gaps.
"""

import enum
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.money import CURRENCY, MoneyColumn
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.billing.discount_usage import DiscountUsage
    from app.models.billing.invoice_line import InvoiceLine
    from app.models.customers.customer import Customer
    from app.models.subscriptions.subscription import Subscription

ZERO = Decimal("0.00")


class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


def invoice_status_column(constraint_name: str, **kwargs):
    return mapped_column(
        Enum(
            InvoiceStatus,
            native_enum=False,
            create_constraint=True,
            name=constraint_name,
            length=20,
        ),
        **kwargs,
    )


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("amount_subtotal >= 0", name="subtotal_non_negative"),
        CheckConstraint("amount_tax >= 0", name="tax_non_negative"),
        CheckConstraint("amount_discount >= 0", name="discount_non_negative"),
        CheckConstraint("amount_total >= 0", name="total_non_negative"),
        CheckConstraint("amount_paid >= 0", name="paid_non_negative"),
        CheckConstraint("due_date >= issue_date", name="dates_valid"),
        # Billing idempotency: only one invoice per subscription per billing cycle period
        UniqueConstraint(
            "subscription_id",
            "period_start",
            "period_end",
            name="uq_invoices_subscription_period",
        ),
        # Indexes required by the 2-second budget and frequent lookups
        Index("ix_invoices_status_due_date", "status", "due_date"),
        Index("ix_invoices_customer_id", "customer_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Auto-generated sequential number, e.g. INV-2026-000001
    number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[InvoiceStatus] = invoice_status_column(
        "invoice_status", nullable=False, default=InvoiceStatus.DRAFT
    )
    issue_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default=CURRENCY)

    amount_subtotal: Mapped[Decimal] = MoneyColumn(nullable=False, default=ZERO)
    amount_tax: Mapped[Decimal] = MoneyColumn(nullable=False, default=ZERO)
    amount_discount: Mapped[Decimal] = MoneyColumn(nullable=False, default=ZERO)
    amount_total: Mapped[Decimal] = MoneyColumn(nullable=False, default=ZERO)
    amount_paid: Mapped[Decimal] = MoneyColumn(nullable=False, default=ZERO)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    lines: Mapped[list["InvoiceLine"]] = relationship(
        "InvoiceLine",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLine.id",
    )
    customer: Mapped["Customer"] = relationship("Customer")
    subscription: Mapped["Subscription"] = relationship("Subscription")
    discount_usages: Mapped[list["DiscountUsage"]] = relationship(
        "DiscountUsage", back_populates="invoice", cascade="all, delete-orphan"
    )

    @hybrid_property
    def amount_due(self) -> Decimal:
        """Remaining balance on the invoice."""
        due = self.amount_total - self.amount_paid
        return due if due > ZERO else ZERO

    @hybrid_property
    def is_overdue(self) -> bool:
        """True if the invoice is unpaid and past its due date."""
        return (
            self.status in (InvoiceStatus.DRAFT, InvoiceStatus.CONFIRMED)
            and self.due_date < date.today()
            and self.amount_due > ZERO
        )


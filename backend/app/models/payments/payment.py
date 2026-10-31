"""Payments recorded against invoices (full or partial)."""

import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.money import MoneyColumn
from app.models.base import Base, TimestampMixin


class PaymentMethod(str, enum.Enum):
    CARD = "CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    UPI = "UPI"
    CASH = "CASH"
    CHEQUE = "CHEQUE"


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Denormalised for scoping and reporting; copied from the invoice at record time.
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = MoneyColumn(nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, native_enum=False, create_constraint=True, name="payment_method", length=20),
        nullable=False,
    )
    paid_at: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    invoice = relationship("Invoice")

"""Discount usage record.

Tracks when and on which invoice a discount rule was consumed,
ensuring discount usage limits are enforced and traceable.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.money import MoneyColumn
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.billing.invoice import Invoice
    from app.models.catalog.discount import Discount
    from app.models.customers.customer import Customer


class DiscountUsage(Base):
    __tablename__ = "discount_usages"
    __table_args__ = (
        CheckConstraint("amount_applied >= 0", name="amount_applied_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    discount_id: Mapped[int] = mapped_column(
        ForeignKey("discounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount_applied: Mapped[Decimal] = MoneyColumn(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    discount: Mapped["Discount"] = relationship("Discount")
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="discount_usages")
    customer: Mapped["Customer"] = relationship("Customer")


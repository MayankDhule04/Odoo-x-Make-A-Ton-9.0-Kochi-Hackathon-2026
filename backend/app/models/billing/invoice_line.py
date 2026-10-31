"""Invoice lines representing products, taxes, and prorations/discounts."""

from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.money import MoneyColumn
from app.models.base import Base

ZERO = Decimal("0.00")


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        CheckConstraint("tax_rate >= 0", name="tax_rate_non_negative"),
        CheckConstraint("tax_amount >= 0", name="tax_amount_non_negative"),
        CheckConstraint("discount_amount >= 0", name="discount_amount_non_negative"),
        CheckConstraint("amount >= 0", name="amount_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    tax_id: Mapped[int | None] = mapped_column(
        ForeignKey("taxes.id", ondelete="SET NULL"), nullable=True
    )

    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    unit_price: Mapped[Decimal] = MoneyColumn(nullable=False, default=ZERO)
    # Stored tax percentage at invoice creation (e.g. 18.000%)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False, default=ZERO)
    tax_amount: Mapped[Decimal] = MoneyColumn(nullable=False, default=ZERO)
    discount_amount: Mapped[Decimal] = MoneyColumn(nullable=False, default=ZERO)
    # Net line total after discount and including tax if exclusive, or line total
    amount: Mapped[Decimal] = MoneyColumn(nullable=False, default=ZERO)
    line_type: Mapped[str] = mapped_column(String(20), nullable=False, default="STANDARD")

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="lines")
    product: Mapped["Product"] = relationship("Product")
    variant: Mapped["ProductVariant"] = relationship("ProductVariant")
    tax: Mapped["Tax"] = relationship("Tax")

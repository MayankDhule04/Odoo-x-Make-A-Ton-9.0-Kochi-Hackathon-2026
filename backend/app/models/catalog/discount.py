"""Admin-only discount rules. Billing (Member 3) applies them as invoice lines and
increments usage_count atomically when an invoice is confirmed."""

import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.money import MoneyColumn
from app.models.base import Base, TimestampMixin


class DiscountType(str, enum.Enum):
    FIXED = "FIXED"
    PERCENTAGE = "PERCENTAGE"


class DiscountTarget(str, enum.Enum):
    PRODUCT = "PRODUCT"
    SUBSCRIPTION = "SUBSCRIPTION"


# A discount rule may be limited to specific products.
discount_products = Table(
    "discount_products",
    Base.metadata,
    Column("discount_id", ForeignKey("discounts.id", ondelete="CASCADE"), primary_key=True),
    Column("product_id", ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
)


class Discount(TimestampMixin, Base):
    __tablename__ = "discounts"
    __table_args__ = (
        CheckConstraint("value >= 0", name="value_non_negative"),
        CheckConstraint("min_purchase_amount >= 0", name="min_purchase_non_negative"),
        CheckConstraint("min_quantity >= 0", name="min_quantity_non_negative"),
        CheckConstraint("usage_limit >= 0", name="usage_limit_non_negative"),
        CheckConstraint("usage_count >= 0", name="usage_count_non_negative"),
        CheckConstraint("end_date >= start_date", name="dates_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType, native_enum=False, create_constraint=True, name="discount_type", length=20),
        nullable=False,
    )
    value: Mapped[Decimal] = MoneyColumn(nullable=False)  # fixed amount, or percent as a number
    min_purchase_amount: Mapped[Decimal] = MoneyColumn(nullable=False, default=Decimal("0.00"))
    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    usage_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")  # 0 = unlimited
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    target: Mapped[DiscountTarget] = mapped_column(
        Enum(DiscountTarget, native_enum=False, create_constraint=True, name="discount_target", length=20),
        nullable=False,
        default=DiscountTarget.SUBSCRIPTION,
    )

    products: Mapped[list["Product"]] = relationship(secondary=discount_products)

    @property
    def product_ids(self) -> list[int]:
        """Ids of the products this discount is limited to (empty = all products)."""
        return [p.id for p in self.products]

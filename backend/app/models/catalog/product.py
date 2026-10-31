"""Products, their attributes and variants.

Effective price of a variant = product base sales price + the variant's price extra
(e.g. the "Odoo" brand variant adds +560). Margin = sales price - cost price.
"""

import enum
from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.money import MoneyColumn
from app.models.base import Base, TimestampMixin

ZERO = Decimal("0.00")


class ProductType(str, enum.Enum):
    SERVICE = "SERVICE"
    SOFTWARE = "SOFTWARE"
    ADDON = "ADDON"
    PHYSICAL = "PHYSICAL"


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("sales_price >= 0", name="sales_price_non_negative"),
        CheckConstraint("cost_price >= 0", name="cost_price_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    type: Mapped[ProductType] = mapped_column(
        Enum(ProductType, native_enum=False, create_constraint=True, name="product_type", length=20),
        nullable=False,
    )
    sales_price: Mapped[Decimal] = MoneyColumn(nullable=False)
    cost_price: Mapped[Decimal] = MoneyColumn(nullable=False, default=ZERO)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")

    attributes: Mapped[list["ProductAttribute"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductAttribute.id"
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductVariant.id"
    )

    @hybrid_property
    def margin(self) -> Decimal:
        """Computed margin = sales price - cost price."""
        return (self.sales_price or ZERO) - (self.cost_price or ZERO)


class ProductAttribute(TimestampMixin, Base):
    __tablename__ = "product_attributes"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "Brand"

    product: Mapped["Product"] = relationship(back_populates="attributes")
    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="attribute")


class ProductVariant(TimestampMixin, Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        CheckConstraint("price_extra >= 0", name="price_extra_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attribute_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_attributes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    value: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "Odoo"
    price_extra: Mapped[Decimal] = MoneyColumn(nullable=False, default=ZERO)  # e.g. 560.00

    product: Mapped["Product"] = relationship(back_populates="variants")
    attribute: Mapped["ProductAttribute | None"] = relationship(back_populates="variants")

    @hybrid_property
    def effective_price(self) -> Decimal:
        """Effective price = product base sales price + this variant's extra."""
        base = self.product.sales_price if self.product else ZERO
        return (base or ZERO) + (self.price_extra or ZERO)

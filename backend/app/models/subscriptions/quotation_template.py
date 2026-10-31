"""Quotation templates: a preset plan + product lines with a validity in days.

A sales rep creates a subscription (quotation) from a template and edits it afterwards.
"""

from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.money import MoneyColumn
from app.models.base import Base, TimestampMixin


class QuotationTemplate(TimestampMixin, Base):
    __tablename__ = "quotation_templates"
    __table_args__ = (
        CheckConstraint("validity_days > 0", name="validity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    validity_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default="30"
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")

    lines: Mapped[list["QuotationTemplateLine"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="QuotationTemplateLine.id"
    )


class QuotationTemplateLine(Base):
    __tablename__ = "quotation_template_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("quotation_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    # Null = use the product's effective price when the subscription is created.
    unit_price: Mapped[Decimal | None] = MoneyColumn(nullable=True)

    template: Mapped["QuotationTemplate"] = relationship(back_populates="lines")

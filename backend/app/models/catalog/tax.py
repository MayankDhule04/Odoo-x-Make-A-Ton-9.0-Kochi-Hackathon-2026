"""Admin-defined tax rules. Billing (Member 3) applies these per invoice line."""

import enum
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Enum, Numeric, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TaxAppliesTo(str, enum.Enum):
    PRODUCT = "PRODUCT"
    CATEGORY = "CATEGORY"


class Tax(TimestampMixin, Base):
    __tablename__ = "taxes"
    __table_args__ = (
        CheckConstraint("percentage >= 0", name="percentage_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Percentage like 18.000; not money, so a plain Numeric with 3 fraction digits.
    percentage: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    applies_to: Mapped[TaxAppliesTo] = mapped_column(
        Enum(TaxAppliesTo, native_enum=False, create_constraint=True, name="tax_applies_to", length=20),
        nullable=False,
        default=TaxAppliesTo.PRODUCT,
    )
    inclusive: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

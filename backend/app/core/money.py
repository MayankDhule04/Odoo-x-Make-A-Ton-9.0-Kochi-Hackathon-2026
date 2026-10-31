"""Money helpers: never a float, always Decimal, always INR.

In the database: Numeric(12, 2)  — up to ₹99,99,99,99,999.99.
In Python: Decimal.
In JSON:   a string like "1250.00" (Pydantic serializes Decimal as str by default).

Usage in a model:
    from app.core.money import MoneyColumn
    price: Mapped[Decimal] = MoneyColumn()

Usage in a schema:
    from app.core.money import MoneyField
    price: Decimal = MoneyField()
"""

from decimal import Decimal

from pydantic import Field
from sqlalchemy import Numeric
from sqlalchemy.orm import mapped_column

# The only supported currency.  Attached to every monetary JSON response so the
# frontend never has to guess.
CURRENCY = "INR"

# Postgres Numeric(12, 2): 10 digits before the decimal point, 2 after.
MONEY_PRECISION = 12
MONEY_SCALE = 2


def MoneyColumn(**kwargs):  # noqa: N802  (looks like a class)
    """Mapped column for money amounts in SQLAlchemy models."""
    return mapped_column(Numeric(precision=MONEY_PRECISION, scale=MONEY_SCALE), **kwargs)


def MoneyField(*, description: str = "Amount in INR.", **kwargs) -> Decimal:  # noqa: N802
    """Pydantic field for money amounts in request and response schemas."""
    return Field(decimal_places=MONEY_SCALE, description=description, **kwargs)

"""Demo catalog for the 5-minute demo script: a product with the Odoo brand variant
(+560), a monthly plan, a tax rule and a discount rule."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import (
    BillingPeriod,
    Discount,
    DiscountType,
    Plan,
    Product,
    ProductAttribute,
    ProductType,
    ProductVariant,
    Tax,
)


def seed_demo_catalog(db: Session) -> list[str]:
    """Create demo catalog rows that don't exist yet. Returns labels of what it created.

    Idempotent: keyed on names, so a restart doesn't duplicate anything.
    """
    created: list[str] = []

    if db.scalar(select(Product.id).where(Product.name == "Brightloop Pro")) is None:
        product = Product(
            name="Brightloop Pro",
            type=ProductType.SOFTWARE,
            sales_price=Decimal("1000.00"),
            cost_price=Decimal("400.00"),
            notes="Flagship software product.",
        )
        product.attributes.append(ProductAttribute(name="Brand"))
        product.variants.append(ProductVariant(value="Generic", price_extra=Decimal("0.00")))
        product.variants.append(ProductVariant(value="Odoo", price_extra=Decimal("560.00")))
        db.add(product)
        created.append("product 'Brightloop Pro' (+560 Odoo variant)")

    if db.scalar(select(Plan.id).where(Plan.name == "Monthly Standard")) is None:
        today = date.today()
        db.add(
            Plan(
                name="Monthly Standard",
                price=Decimal("999.00"),
                billing_period=BillingPeriod.MONTHLY,
                min_quantity=1,
                available_from=today - timedelta(days=30),
                available_to=today + timedelta(days=365),
            )
        )
        created.append("plan 'Monthly Standard'")

    if db.scalar(select(Tax.id).where(Tax.name == "GST 18%")) is None:
        db.add(Tax(name="GST 18%", percentage=Decimal("18.000")))
        created.append("tax 'GST 18%'")

    if db.scalar(select(Discount.id).where(Discount.name == "Launch 10%")) is None:
        today = date.today()
        db.add(
            Discount(
                name="Launch 10%",
                type=DiscountType.PERCENTAGE,
                value=Decimal("10.00"),
                start_date=today - timedelta(days=1),
                end_date=today + timedelta(days=90),
                usage_limit=0,
            )
        )
        created.append("discount 'Launch 10%'")

    return created

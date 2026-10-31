"""Catalog models (Member 2). Import each model class here so Alembic sees it."""

from app.models.catalog.discount import (
    Discount,
    DiscountTarget,
    DiscountType,
    discount_products,
)
from app.models.catalog.plan import BillingPeriod, Plan
from app.models.catalog.product import (
    Product,
    ProductAttribute,
    ProductType,
    ProductVariant,
)
from app.models.catalog.tax import Tax, TaxAppliesTo

__all__ = [
    "Discount",
    "DiscountTarget",
    "DiscountType",
    "discount_products",
    "Plan",
    "BillingPeriod",
    "Product",
    "ProductAttribute",
    "ProductVariant",
    "ProductType",
    "Tax",
    "TaxAppliesTo",
]

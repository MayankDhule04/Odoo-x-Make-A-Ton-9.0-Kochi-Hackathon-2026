"""Catalog endpoints (Member 2): products, variants, plans, tax rules and discount
rules. Quotation templates arrive with subscriptions (Phase 3).

Each resource lives in its own module; they are combined into one router here, which
app/api/router.py mounts under /api.
"""

from fastapi import APIRouter

from app.api.catalog import discounts, plans, products, taxes

router = APIRouter(tags=["catalog"])
router.include_router(products.router)
router.include_router(plans.router)
router.include_router(taxes.router)
router.include_router(discounts.router)

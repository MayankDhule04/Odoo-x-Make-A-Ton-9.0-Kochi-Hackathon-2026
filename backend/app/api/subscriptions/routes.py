"""Subscription endpoints (Member 2): quotation templates, subscriptions and lifecycle
transitions. Proration and the discount simulator (differentiators) come later.

Each resource lives in its own module; they are combined here and mounted under /api.
"""

from fastapi import APIRouter

from app.api.subscriptions import subscriptions, templates

router = APIRouter(tags=["subscriptions"])
router.include_router(templates.router)
router.include_router(subscriptions.router)

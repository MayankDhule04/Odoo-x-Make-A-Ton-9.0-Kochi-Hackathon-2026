"""Top-level API router, mounted under /api.

Every domain router is already included, so each member only edits files inside their
own app/api/<domain>/ package.
"""

from fastapi import APIRouter

from app.api import auth, billing, catalog, health, payments, reporting, subscriptions

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(subscriptions.router)
api_router.include_router(billing.router)
api_router.include_router(payments.router)
api_router.include_router(reporting.router)

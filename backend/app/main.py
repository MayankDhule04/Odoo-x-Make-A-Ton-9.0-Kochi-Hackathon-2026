"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.router import api_router
from app.core.errors import register_error_handlers


def create_app() -> FastAPI:
    application = FastAPI(
        title="Brightloop Subscriptions API",
        version="0.1.0",
        # Served under /api so the docs also work through the web dev server proxy.
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    register_error_handlers(application)
    application.include_router(api_router, prefix="/api")
    return application


app = create_app()

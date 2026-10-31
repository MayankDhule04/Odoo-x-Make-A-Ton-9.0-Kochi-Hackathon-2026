"""Model registry.

Importing this package imports every domain's models, so Alembic autogenerate and the
tests see all tables. Add new models to your domain's own __init__.py, not here.
"""

# Base must be imported before the domain packages, which import it.
from app.models.base import Base, TimestampMixin
from app.models import auth, billing, catalog, payments, subscriptions  # noqa: F401

__all__ = ["Base", "TimestampMixin"]

"""Auth and audit models (Member 1). Import each model class here so Alembic sees it."""

from app.models.auth.user import User, UserRole

__all__ = ["User", "UserRole"]

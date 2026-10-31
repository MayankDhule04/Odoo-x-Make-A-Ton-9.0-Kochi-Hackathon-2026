"""Helpers that any domain's tests can import (fixtures live in conftest.py)."""

from app.core.security import create_access_token
from app.models.auth import User

# Password used for every user the fixtures create. It satisfies the password policy.
TEST_PASSWORD = "Test@Pass123"


def auth_headers(user: User) -> dict[str, str]:
    """Authorization header carrying a fresh access token for `user`."""
    token = create_access_token(user_id=user.id, token_version=user.token_version).token
    return {"Authorization": f"Bearer {token}"}

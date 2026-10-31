"""Account services (Member 1): creating users and checking credentials."""

from app.services.auth.accounts import (
    EmailAlreadyRegisteredError,
    PasswordPolicyError,
    authenticate,
    create_user,
    normalize_email,
)
from app.services.auth.password_reset import (
    InvalidResetTokenError,
    request_password_reset,
    reset_password,
)

__all__ = [
    "EmailAlreadyRegisteredError",
    "InvalidResetTokenError",
    "PasswordPolicyError",
    "authenticate",
    "create_user",
    "normalize_email",
    "request_password_reset",
    "reset_password",
]

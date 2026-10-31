"""Forgot and reset password.

- request_password_reset(): creates a token and emails the link. Returns success
  whether or not the email exists, so accounts can't be discovered.
- reset_password(): validates the token and sets the new password.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, password_policy_errors
from app.models.auth import User
from app.models.auth.password_reset_token import PasswordResetToken
from app.services.auth.accounts import PasswordPolicyError, normalize_email
from app.services.email import send_email

RESET_TOKEN_TTL_MINUTES = 30
RESET_TOKEN_BYTES = 32


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def request_password_reset(db: Session, *, email: str, base_url: str) -> None:
    """Always succeeds (from the caller's perspective) so it never reveals whether
    the email exists."""
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None or not user.is_active:
        return

    raw_token = secrets.token_urlsafe(RESET_TOKEN_BYTES)
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
    )
    db.add(reset)
    db.flush()

    link = f"{base_url}/reset-password?token={raw_token}"
    send_email(
        db,
        to=user.email,
        subject="Brightloop — Reset your password",
        body=(
            f"<p>Hi {user.full_name},</p>"
            f"<p>Click the link below to reset your password. It expires in {RESET_TOKEN_TTL_MINUTES} minutes.</p>"
            f'<p><a href="{link}">{link}</a></p>'
            "<p>If you didn't request this, you can ignore this email.</p>"
        ),
    )


class InvalidResetTokenError(ValueError):
    def __init__(self) -> None:
        super().__init__("This reset link is invalid or has expired.")


def reset_password(db: Session, *, raw_token: str, new_password: str) -> User:
    """Validate the token, set the new password, revoke all sessions.

    Raises InvalidResetTokenError or PasswordPolicyError.
    """
    errors = password_policy_errors(new_password)
    if errors:
        raise PasswordPolicyError(errors)

    token_hash = _hash_token(raw_token)
    now = datetime.now(timezone.utc)

    reset = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used.is_(False),
            PasswordResetToken.expires_at > now,
        )
    )
    if reset is None:
        raise InvalidResetTokenError()

    reset.used = True
    user = db.get(User, reset.user_id)
    if user is None:
        raise InvalidResetTokenError()

    user.password_hash = hash_password(new_password)
    # Bump the version so all existing tokens (access + refresh) are revoked.
    user.token_version += 1
    db.flush()
    return user

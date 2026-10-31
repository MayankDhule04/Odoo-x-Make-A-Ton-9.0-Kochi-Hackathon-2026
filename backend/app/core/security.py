"""Password hashing (argon2), the password policy, and JWT access and refresh tokens."""

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings

# --- Password policy -----------------------------------------------------------------

# "More than 8 characters" means 9 or more.
PASSWORD_MIN_LENGTH = 9
PASSWORD_MAX_LENGTH = 128
_SPECIAL_CHARACTER = re.compile(r"[^A-Za-z0-9\s]")


def password_policy_errors(password: str) -> list[str]:
    """Return every rule the password breaks, as messages a user can act on.

    An empty list means the password is acceptable.
    """
    errors = []
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"Use at least {PASSWORD_MIN_LENGTH} characters.")
    if len(password) > PASSWORD_MAX_LENGTH:
        errors.append(f"Use at most {PASSWORD_MAX_LENGTH} characters.")
    if not any(char.isupper() for char in password):
        errors.append("Add at least one uppercase letter.")
    if not any(char.islower() for char in password):
        errors.append("Add at least one lowercase letter.")
    if not _SPECIAL_CHARACTER.search(password):
        errors.append("Add at least one special character, such as ! @ # or $.")
    return errors


# --- Password hashing ----------------------------------------------------------------

_hasher = PasswordHasher()
# Checking a password against this hash when the email is unknown makes a failed login
# take the same time whether or not the account exists.
_DUMMY_HASH = _hasher.hash("timing-equalizer-not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def spend_password_check_time(password: str) -> None:
    """Do the work of a password check when there is no account to check against."""
    verify_password(_DUMMY_HASH, password)


# --- JWT tokens ----------------------------------------------------------------------

JWT_ALGORITHM = "HS256"
TokenType = Literal["access", "refresh"]


class InvalidTokenError(Exception):
    """The token is malformed, expired, wrongly signed, or of the wrong type."""


@dataclass(frozen=True)
class IssuedToken:
    token: str
    expires_at: datetime


def _issue_token(*, user_id: int, token_version: int, token_type: TokenType, ttl: timedelta) -> IssuedToken:
    now = datetime.now(timezone.utc)
    expires_at = now + ttl
    payload: dict[str, Any] = {
        "sub": str(user_id),
        # Must match users.token_version; bumping that column revokes every token.
        "ver": token_version,
        "type": token_type,
        "iat": now,
        "exp": expires_at,
        "jti": uuid.uuid4().hex,
    }
    return IssuedToken(jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM), expires_at)


def create_access_token(*, user_id: int, token_version: int) -> IssuedToken:
    return _issue_token(
        user_id=user_id,
        token_version=token_version,
        token_type="access",
        ttl=timedelta(minutes=settings.access_token_ttl_minutes),
    )


def create_refresh_token(*, user_id: int, token_version: int) -> IssuedToken:
    return _issue_token(
        user_id=user_id,
        token_version=token_version,
        token_type="refresh",
        ttl=timedelta(days=settings.refresh_token_ttl_days),
    )


def decode_token(token: str, *, expected_type: TokenType) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub", "type", "ver"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"Expected a {expected_type} token.")
    return payload

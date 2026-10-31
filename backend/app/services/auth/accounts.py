"""Creating user accounts and checking credentials.

Services flush but never commit; the route or script that calls them commits once.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    hash_password,
    password_needs_rehash,
    password_policy_errors,
    spend_password_check_time,
    verify_password,
)
from app.models.auth import User, UserRole
from app.models.customers import Customer

_USERS_EMAIL_UNIQUE = "uq_users_email"


class PasswordPolicyError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__(" ".join(errors))
        self.errors = errors


class EmailAlreadyRegisteredError(ValueError):
    def __init__(self) -> None:
        super().__init__("An account with this email already exists.")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    role: UserRole,
) -> User:
    """Create a user. A CUSTOMER also gets the customer record that scopes their data.

    Raises PasswordPolicyError or EmailAlreadyRegisteredError. Emails are unique
    regardless of case; the database enforces it, so concurrent sign-ups can't race.
    """
    errors = password_policy_errors(password)
    if errors:
        raise PasswordPolicyError(errors)

    clean_name = full_name.strip()
    user = User(
        email=normalize_email(email),
        password_hash=hash_password(password),
        full_name=clean_name,
        role=role,
    )
    try:
        # The savepoint keeps the caller's transaction usable if the insert fails.
        with db.begin_nested():
            db.add(user)
            db.flush()
    except IntegrityError as exc:
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == _USERS_EMAIL_UNIQUE:
            raise EmailAlreadyRegisteredError() from exc
        raise

    if role is UserRole.CUSTOMER:
        db.add(Customer(user_id=user.id, name=clean_name, email=user.email))
        db.flush()
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Return the active user with these credentials, or None.

    Unknown email, wrong password and deactivated account all return None, so callers
    give the same answer in every case and don't reveal which accounts exist.
    """
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None:
        spend_password_check_time(password)
        return None
    if not verify_password(user.password_hash, password) or not user.is_active:
        return None
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    return user

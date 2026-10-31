"""The three demo accounts listed in the README."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User, UserRole
from app.services.auth import create_user


@dataclass(frozen=True)
class DemoUser:
    email: str
    password: str
    full_name: str
    role: UserRole


# Development-only credentials, documented in the README for the demo.
DEMO_USERS = (
    DemoUser("admin@brightloop.dev", "Admin@12345", "Demo Admin", UserRole.ADMIN),
    DemoUser("staff@brightloop.dev", "Staff@12345", "Demo Staff", UserRole.STAFF),
    DemoUser("customer@brightloop.dev", "Customer@12345", "Demo Customer", UserRole.CUSTOMER),
)


def seed_demo_users(db: Session) -> list[str]:
    """Create any demo account that doesn't exist yet. Returns the emails it created.

    Existing accounts are left alone, so a changed password survives a restart.
    """
    created = []
    for demo in DEMO_USERS:
        if db.scalar(select(User.id).where(User.email == demo.email)) is None:
            create_user(db, email=demo.email, password=demo.password, full_name=demo.full_name, role=demo.role)
            created.append(demo.email)
    return created

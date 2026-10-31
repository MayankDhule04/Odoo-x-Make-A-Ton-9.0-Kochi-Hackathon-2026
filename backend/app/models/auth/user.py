"""User accounts for all three roles."""

import enum

from sqlalchemy import Boolean, Enum, Integer, String, true
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    STAFF = "STAFF"
    ADMIN = "ADMIN"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # CITEXT makes the unique constraint case-insensitive inside the database, so
    # "Ana@x.com" and "ana@x.com" can never both exist, whichever code path inserts them.
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, create_constraint=True, name="user_role", length=20),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    # Every token carries this number. Incrementing it (password reset, deactivation)
    # makes all of the user's existing tokens invalid at once.
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

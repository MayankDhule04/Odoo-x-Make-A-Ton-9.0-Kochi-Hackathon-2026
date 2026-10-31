"""Customers: the people and companies that subscribe and get invoiced."""

from sqlalchemy import Boolean, ForeignKey, String, Text, true
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Customer(TimestampMixin, Base):
    """Subscriptions, invoices and payments reference customers.id.

    A customer who signs up gets a linked login (user_id). Staff can also add customers
    who never log in, so user_id is nullable.
    """

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), unique=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Billing contact email; for a self-signed-up customer it starts as the login email.
    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    billing_address: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())

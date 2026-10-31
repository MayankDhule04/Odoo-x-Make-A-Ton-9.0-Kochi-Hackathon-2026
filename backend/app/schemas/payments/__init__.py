"""Request and response schemas for payments, dunning and revenue-at-risk."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.money import MoneyField
from app.models.payments import DunningKind, PaymentMethod

_FROM_ATTR = ConfigDict(from_attributes=True)


# --- Payments ------------------------------------------------------------------------

class PaymentCreate(BaseModel):
    invoice_id: int
    amount: Decimal = MoneyField(gt=0)
    method: PaymentMethod
    paid_at: date = Field(default_factory=date.today)
    note: str | None = None


class PaymentRead(BaseModel):
    model_config = _FROM_ATTR
    id: int
    invoice_id: int
    customer_id: int
    amount: Decimal
    method: PaymentMethod
    paid_at: date
    note: str | None
    created_at: datetime


class PaymentStatusSummary(BaseModel):
    """Counts of invoices by derived payment state, and the money still owed."""
    paid: int
    partially_paid: int
    outstanding: int
    overdue: int
    total_outstanding: Decimal
    total_overdue: Decimal


# --- Dunning -------------------------------------------------------------------------

class DunningAttemptRead(BaseModel):
    model_config = _FROM_ATTR
    id: int
    invoice_id: int
    subscription_id: int | None
    attempt_number: int
    kind: DunningKind
    days_overdue: int
    note: str | None
    created_at: datetime


class DunningRunRequest(BaseModel):
    as_of_date: date | None = None


class DunningRunResponse(BaseModel):
    as_of_date: date
    invoices_processed: int
    reminders_sent: int
    suspensions: int


# --- Revenue at risk -----------------------------------------------------------------

class RevenueAtRiskItem(BaseModel):
    subscription_id: int
    subscription_number: str
    customer_id: int
    customer_name: str
    overdue_amount: Decimal
    days_overdue: int
    invoice_count: int


class RevenueAtRiskResponse(BaseModel):
    total_at_risk: Decimal
    items: list[RevenueAtRiskItem]


class MessageResponse(BaseModel):
    message: str

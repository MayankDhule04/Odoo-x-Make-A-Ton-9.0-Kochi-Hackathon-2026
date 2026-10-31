"""Request and response models for quotations and subscriptions."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.money import MoneyField
from app.models.subscriptions import PaymentTerms, SubscriptionStatus

_FROM_ATTR = ConfigDict(from_attributes=True)


# --- Quotation templates -------------------------------------------------------------

class TemplateLineIn(BaseModel):
    product_id: int
    variant_id: int | None = None
    quantity: int = Field(default=1, gt=0)
    unit_price: Decimal | None = MoneyField(default=None, ge=0)


class TemplateLineRead(BaseModel):
    model_config = _FROM_ATTR
    id: int
    product_id: int
    variant_id: int | None
    quantity: int
    unit_price: Decimal | None


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    plan_id: int
    validity_days: int = Field(default=30, gt=0)
    notes: str = ""
    lines: list[TemplateLineIn] = []


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    plan_id: int | None = None
    validity_days: int | None = Field(default=None, gt=0)
    notes: str | None = None
    lines: list[TemplateLineIn] | None = None


class TemplateRead(BaseModel):
    model_config = _FROM_ATTR
    id: int
    name: str
    plan_id: int
    validity_days: int
    notes: str
    lines: list[TemplateLineRead]


# --- Subscriptions -------------------------------------------------------------------

class SubscriptionLineIn(BaseModel):
    product_id: int
    variant_id: int | None = None
    tax_id: int | None = None
    quantity: int = Field(default=1, gt=0)
    # Null = derive from the product's effective price.
    unit_price: Decimal | None = MoneyField(default=None, ge=0)


class SubscriptionLineRead(BaseModel):
    model_config = _FROM_ATTR
    id: int
    product_id: int
    variant_id: int | None
    tax_id: int | None
    quantity: int
    unit_price: Decimal
    amount: Decimal


class SubscriptionCreate(BaseModel):
    customer_id: int
    plan_id: int
    start_date: date
    expiry_date: date
    payment_terms: PaymentTerms = PaymentTerms.IMMEDIATE
    lines: list[SubscriptionLineIn] = []


class SubscriptionFromTemplate(BaseModel):
    template_id: int
    customer_id: int
    start_date: date
    # Null = start_date + the template's validity_days.
    expiry_date: date | None = None
    payment_terms: PaymentTerms = PaymentTerms.IMMEDIATE


class SubscriptionUpdate(BaseModel):
    """Edits allowed only while DRAFT or QUOTATION."""
    plan_id: int | None = None
    start_date: date | None = None
    expiry_date: date | None = None
    payment_terms: PaymentTerms | None = None
    lines: list[SubscriptionLineIn] | None = None


class SubscriptionHistoryRead(BaseModel):
    model_config = _FROM_ATTR
    id: int
    from_status: SubscriptionStatus | None
    to_status: SubscriptionStatus
    actor_id: int | None
    note: str | None
    created_at: datetime


class SubscriptionRead(BaseModel):
    model_config = _FROM_ATTR
    id: int
    number: str
    customer_id: int
    plan_id: int
    start_date: date
    expiry_date: date
    next_billing_date: date | None
    payment_terms: PaymentTerms
    status: SubscriptionStatus
    amount_total: Decimal
    lines: list[SubscriptionLineRead]


class SubscriptionDetail(SubscriptionRead):
    history: list[SubscriptionHistoryRead]


class TransitionRequest(BaseModel):
    """Optional note attached to a lifecycle action."""
    note: str | None = None


class GenericTransitionRequest(TransitionRequest):
    to_status: SubscriptionStatus

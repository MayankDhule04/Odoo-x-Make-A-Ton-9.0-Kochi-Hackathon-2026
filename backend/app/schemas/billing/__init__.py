"""Request and response schemas for invoices and billing runs."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.money import CURRENCY, MoneyField
from app.models.billing import InvoiceStatus

_FROM_ATTR = ConfigDict(from_attributes=True)


# --- Invoice lines -------------------------------------------------------------------

class InvoiceLineIn(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    quantity: int = Field(default=1, gt=0)
    unit_price: Decimal = MoneyField(ge=0)
    product_id: int | None = None
    variant_id: int | None = None
    tax_id: int | None = None
    tax_rate: Decimal = Field(default=Decimal("0.000"), ge=0)
    tax_amount: Decimal = MoneyField(default=Decimal("0.00"), ge=0)
    discount_amount: Decimal = MoneyField(default=Decimal("0.00"), ge=0)
    amount: Decimal = MoneyField(default=Decimal("0.00"), ge=0)
    line_type: str = "STANDARD"


class InvoiceLineRead(BaseModel):
    model_config = _FROM_ATTR
    id: int
    invoice_id: int
    product_id: int | None
    variant_id: int | None
    tax_id: int | None
    description: str
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    amount: Decimal
    line_type: str


# --- Invoices ------------------------------------------------------------------------

class InvoiceCreate(BaseModel):
    customer_id: int
    subscription_id: int | None = None
    issue_date: date = Field(default_factory=date.today)
    due_date: date
    period_start: date | None = None
    period_end: date | None = None
    notes: str | None = None
    lines: list[InvoiceLineIn] = Field(min_length=1)


class InvoiceCustomerRead(BaseModel):
    model_config = _FROM_ATTR
    id: int
    name: str
    email: str
    billing_address: str | None = None
    phone: str | None = None


class InvoiceRead(BaseModel):
    model_config = _FROM_ATTR
    id: int
    number: str
    customer_id: int
    subscription_id: int | None
    status: InvoiceStatus
    issue_date: date
    due_date: date
    period_start: date | None
    period_end: date | None
    currency: str = CURRENCY
    amount_subtotal: Decimal
    amount_tax: Decimal
    amount_discount: Decimal
    amount_total: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    is_overdue: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
    lines: list[InvoiceLineRead] = []
    customer: InvoiceCustomerRead | None = None


class InvoiceDetail(InvoiceRead):
    pass


class InvoiceActionRequest(BaseModel):
    note: str | None = None


# --- Dry-run preview & billing run ---------------------------------------------------

class DryRunInvoiceItem(BaseModel):
    subscription_id: int
    subscription_number: str
    customer_id: int
    customer_name: str
    period_start: date
    period_end: date
    due_date: date
    amount_subtotal: Decimal
    amount_tax: Decimal
    amount_discount: Decimal
    amount_total: Decimal
    lines_count: int


class DryRunExceptionItem(BaseModel):
    subscription_id: int
    subscription_number: str
    customer_id: int
    customer_name: str
    error_code: str  # e.g. "EXPIRED_PLAN", "INACTIVE_CUSTOMER", "MISSING_CONTACT"
    severity: Literal["WARNING", "BLOCKER"]
    message: str
    recommendation: str


class DryRunResponse(BaseModel):
    as_of_date: date
    projected_invoices_count: int
    projected_total_amount: Decimal
    exceptions_count: int
    projected_invoices: list[DryRunInvoiceItem]
    exceptions: list[DryRunExceptionItem]


class BillingRunRequest(BaseModel):
    as_of_date: date | None = None


class BillingRunResponse(BaseModel):
    as_of_date: date
    created_count: int
    skipped_count: int
    total_amount: Decimal
    invoices: list[InvoiceRead]

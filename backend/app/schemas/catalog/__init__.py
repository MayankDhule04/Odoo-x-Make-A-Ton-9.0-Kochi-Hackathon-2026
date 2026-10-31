"""Request and response models for the catalog endpoints (products, variants, plans,
tax rules, discount rules)."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.money import MoneyField
from app.models.catalog import (
    BillingPeriod,
    DiscountTarget,
    DiscountType,
    ProductType,
    TaxAppliesTo,
)

_FROM_ATTR = ConfigDict(from_attributes=True)


# --- Products / attributes / variants ------------------------------------------------

class ProductAttributeIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ProductAttributeRead(BaseModel):
    model_config = _FROM_ATTR
    id: int
    name: str


class ProductVariantIn(BaseModel):
    value: str = Field(min_length=1, max_length=100)
    price_extra: Decimal = MoneyField(default=Decimal("0.00"), ge=0)
    attribute_id: int | None = None


class ProductVariantUpdate(BaseModel):
    value: str | None = Field(default=None, min_length=1, max_length=100)
    price_extra: Decimal | None = MoneyField(default=None, ge=0)
    attribute_id: int | None = None


class ProductVariantRead(BaseModel):
    model_config = _FROM_ATTR
    id: int
    value: str
    price_extra: Decimal
    attribute_id: int | None
    effective_price: Decimal


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: ProductType
    sales_price: Decimal = MoneyField(ge=0)
    cost_price: Decimal = MoneyField(default=Decimal("0.00"), ge=0)
    notes: str = ""
    attributes: list[ProductAttributeIn] = []
    variants: list[ProductVariantIn] = []


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    type: ProductType | None = None
    sales_price: Decimal | None = MoneyField(default=None, ge=0)
    cost_price: Decimal | None = MoneyField(default=None, ge=0)
    notes: str | None = None


class ProductRead(BaseModel):
    model_config = _FROM_ATTR
    id: int
    name: str
    type: ProductType
    sales_price: Decimal
    cost_price: Decimal
    notes: str
    margin: Decimal
    attributes: list[ProductAttributeRead]
    variants: list[ProductVariantRead]


# --- Plans ---------------------------------------------------------------------------

class PlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price: Decimal = MoneyField(ge=0)
    billing_period: BillingPeriod
    min_quantity: int = Field(default=1, ge=1)
    available_from: date
    available_to: date
    auto_close: bool = True
    allow_early_close: bool = True
    allow_pause: bool = True
    allow_renew: bool = True

    @model_validator(mode="after")
    def _window_valid(self) -> "PlanCreate":
        if self.available_to < self.available_from:
            raise ValueError("available_to must be on or after available_from")
        return self


class PlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    price: Decimal | None = MoneyField(default=None, ge=0)
    billing_period: BillingPeriod | None = None
    min_quantity: int | None = Field(default=None, ge=1)
    available_from: date | None = None
    available_to: date | None = None
    auto_close: bool | None = None
    allow_early_close: bool | None = None
    allow_pause: bool | None = None
    allow_renew: bool | None = None


class PlanRead(BaseModel):
    model_config = _FROM_ATTR
    id: int
    name: str
    price: Decimal
    billing_period: BillingPeriod
    min_quantity: int
    available_from: date
    available_to: date
    auto_close: bool
    allow_early_close: bool
    allow_pause: bool
    allow_renew: bool


# --- Taxes ---------------------------------------------------------------------------

class TaxCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    percentage: Decimal = Field(ge=0, decimal_places=3)
    applies_to: TaxAppliesTo = TaxAppliesTo.PRODUCT
    inclusive: bool = False


class TaxUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    percentage: Decimal | None = Field(default=None, ge=0, decimal_places=3)
    applies_to: TaxAppliesTo | None = None
    inclusive: bool | None = None


class TaxRead(BaseModel):
    model_config = _FROM_ATTR
    id: int
    name: str
    percentage: Decimal
    applies_to: TaxAppliesTo
    inclusive: bool


# --- Discounts -----------------------------------------------------------------------

class DiscountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: DiscountType
    value: Decimal = MoneyField(ge=0)
    min_purchase_amount: Decimal = MoneyField(default=Decimal("0.00"), ge=0)
    min_quantity: int = Field(default=0, ge=0)
    start_date: date
    end_date: date
    usage_limit: int = Field(default=0, ge=0)
    target: DiscountTarget = DiscountTarget.SUBSCRIPTION
    product_ids: list[int] = []

    @model_validator(mode="after")
    def _dates_valid(self) -> "DiscountCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class DiscountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: DiscountType | None = None
    value: Decimal | None = MoneyField(default=None, ge=0)
    min_purchase_amount: Decimal | None = MoneyField(default=None, ge=0)
    min_quantity: int | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    usage_limit: int | None = Field(default=None, ge=0)
    target: DiscountTarget | None = None
    product_ids: list[int] | None = None

    @model_validator(mode="after")
    def _dates_valid(self) -> "DiscountUpdate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class DiscountSimulateRequest(BaseModel):
    """A draft rule to simulate against current active subscriptions."""
    type: DiscountType
    value: Decimal = MoneyField(ge=0)
    min_purchase_amount: Decimal = MoneyField(default=Decimal("0.00"), ge=0)
    min_quantity: int = Field(default=0, ge=0)
    target: DiscountTarget = DiscountTarget.SUBSCRIPTION
    product_ids: list[int] = []


class DiscountSimulationResult(BaseModel):
    active_subscriptions: int
    matched_count: int
    projected_monthly_impact: Decimal
    currency: str = "INR"


class DiscountRead(BaseModel):
    model_config = _FROM_ATTR
    id: int
    name: str
    type: DiscountType
    value: Decimal
    min_purchase_amount: Decimal
    min_quantity: int
    start_date: date
    end_date: date
    usage_limit: int
    usage_count: int
    target: DiscountTarget
    product_ids: list[int] = []

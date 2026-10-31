"""Schemas for the finance dashboard and MRR analytics."""

from decimal import Decimal

from pydantic import BaseModel

from app.core.money import CURRENCY


class DashboardSummary(BaseModel):
    active_subscriptions: int
    revenue_collected: Decimal
    amount_owed: Decimal
    overdue_count: int
    overdue_amount: Decimal
    customers: int
    currency: str = CURRENCY


class MrrWaterfallEntry(BaseModel):
    month: str  # "2026-10"
    new: Decimal
    expansion: Decimal
    contraction: Decimal
    churn: Decimal
    net: Decimal


class MrrAnalytics(BaseModel):
    mrr: Decimal
    arr: Decimal
    arpu: Decimal
    active_subscriptions: int
    active_customers: int
    churn_rate: Decimal  # percentage, e.g. 4.50 = 4.5%
    waterfall: list[MrrWaterfallEntry]
    currency: str = CURRENCY

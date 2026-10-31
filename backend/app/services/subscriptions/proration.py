"""Proration engine (differentiator #2).

A mid-cycle change computes, for the time left in the current billing period:
  credit = -(current lines total) * remaining_fraction   (refund the unused part)
  charge = +(new lines total)     * remaining_fraction    (charge the new config)
  net    = credit + charge

preview_change returns the breakdown without touching anything. apply_change replaces the
subscription's lines and records the credit/charge as ProrationAdjustment rows for billing.
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.catalog import BillingPeriod, Plan
from app.models.subscriptions import (
    ProrationAdjustment,
    Subscription,
    SubscriptionLine,
    SubscriptionStatus,
)
from app.schemas.subscriptions import SubscriptionLineIn
from app.services.audit import record_audit
from app.services.subscriptions.subscriptions import _effective_unit_price
from app.services.subscriptions.transitions import TransitionError

ZERO = Decimal("0.00")
CENTS = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def _add_months(d: date, months: int) -> date:
    index = d.month - 1 + months
    year = d.year + index // 12
    month = index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _period_start(period_end: date, billing_period: BillingPeriod) -> date:
    """Start of the current billing period, one plan period before its end."""
    if billing_period is BillingPeriod.DAILY:
        return period_end - timedelta(days=1)
    if billing_period is BillingPeriod.WEEKLY:
        return period_end - timedelta(days=7)
    if billing_period is BillingPeriod.MONTHLY:
        return _add_months(period_end, -1)
    return _add_months(period_end, -12)  # YEARLY


def remaining_fraction(sub: Subscription, plan: Plan, today: date) -> Decimal:
    """Fraction of the current billing period still unused (0..1)."""
    period_end = sub.next_billing_date or sub.expiry_date
    period_start = _period_start(period_end, plan.billing_period)
    total_days = (period_end - period_start).days
    if total_days <= 0:
        return ZERO
    remaining = (period_end - today).days
    remaining = max(0, min(remaining, total_days))
    return Decimal(remaining) / Decimal(total_days)


@dataclass(frozen=True)
class ResolvedLine:
    data: SubscriptionLineIn
    unit_price: Decimal
    amount: Decimal


@dataclass(frozen=True)
class Proration:
    remaining_fraction: Decimal
    old_total: Decimal
    new_total: Decimal
    credit: Decimal
    charge: Decimal
    net: Decimal
    resolved: list[ResolvedLine]


def compute(db: Session, sub: Subscription, new_lines: list[SubscriptionLineIn], *, today: date | None = None) -> Proration:
    plan = db.get(Plan, sub.plan_id)
    if plan is None:
        raise TransitionError("The subscription's plan no longer exists.")
    today = today or date.today()
    fraction = remaining_fraction(sub, plan, today)

    old_total = sum((line.amount for line in sub.lines), ZERO)

    resolved: list[ResolvedLine] = []
    new_total = ZERO
    for line in new_lines:
        unit_price = (
            line.unit_price
            if line.unit_price is not None
            else _effective_unit_price(db, line.product_id, line.variant_id)
        )
        amount = _money(unit_price * line.quantity)
        new_total += amount
        resolved.append(ResolvedLine(data=line, unit_price=unit_price, amount=amount))

    credit = _money(-(old_total * fraction))
    charge = _money(new_total * fraction)
    net = _money(credit + charge)
    return Proration(
        remaining_fraction=fraction.quantize(Decimal("0.0001")),
        old_total=_money(old_total),
        new_total=_money(new_total),
        credit=credit,
        charge=charge,
        net=net,
        resolved=resolved,
    )


def preview_change(db: Session, sub: Subscription, new_lines: list[SubscriptionLineIn]) -> Proration:
    return compute(db, sub, new_lines)


def apply_change(
    db: Session,
    sub: Subscription,
    new_lines: list[SubscriptionLineIn],
    *,
    actor: User,
    note: str | None = None,
) -> tuple[Subscription, list[ProrationAdjustment], Proration]:
    if sub.status is not SubscriptionStatus.ACTIVE:
        raise TransitionError("Proration changes can only be applied to an active subscription.")

    proration = compute(db, sub, new_lines)

    # Replace the lines with the new configuration.
    sub.lines.clear()
    db.flush()
    for item in proration.resolved:
        sub.lines.append(
            SubscriptionLine(
                product_id=item.data.product_id,
                variant_id=item.data.variant_id,
                tax_id=item.data.tax_id,
                quantity=item.data.quantity,
                unit_price=item.unit_price,
                amount=item.amount,
            )
        )

    adjustments: list[ProrationAdjustment] = []
    if proration.credit != ZERO:
        adjustments.append(
            ProrationAdjustment(
                subscription_id=sub.id,
                description="Proration credit for unused part of the current period",
                amount=proration.credit,
            )
        )
    if proration.charge != ZERO:
        adjustments.append(
            ProrationAdjustment(
                subscription_id=sub.id,
                description="Proration charge for the new configuration",
                amount=proration.charge,
            )
        )
    for adj in adjustments:
        db.add(adj)

    db.flush()
    record_audit(
        db, actor=actor, entity_type="subscription", entity_id=sub.id, action="proration",
        changes={
            "net": str(proration.net),
            "credit": str(proration.credit),
            "charge": str(proration.charge),
            "note": note,
        },
    )
    return sub, adjustments, proration


def pending_adjustments(subscription_id: int) -> Select:
    """Unapplied adjustments for a subscription; billing consumes these."""
    return (
        select(ProrationAdjustment)
        .where(
            ProrationAdjustment.subscription_id == subscription_id,
            ProrationAdjustment.applied.is_(False),
        )
        .order_by(ProrationAdjustment.id)
    )


def adjustments_query(subscription_id: int) -> Select:
    return (
        select(ProrationAdjustment)
        .where(ProrationAdjustment.subscription_id == subscription_id)
        .order_by(ProrationAdjustment.id)
    )

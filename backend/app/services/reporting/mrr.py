"""MRR analytics (#3): current MRR/ARR/ARPU/churn and a monthly New/Expansion/
Contraction/Churn waterfall.

MRR per subscription = its line total normalised to a month by the plan's period.
The waterfall uses subscription_history (first activation = New, closure = Churn) and
proration_adjustments (positive = Expansion, negative = Contraction). New/Churn amounts
are estimated from ARPU, which is enough for a clear, demoable waterfall.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.catalog import BillingPeriod, Plan
from app.models.subscriptions import (
    ProrationAdjustment,
    Subscription,
    SubscriptionHistory,
    SubscriptionLine,
    SubscriptionStatus,
)
from app.schemas.reporting import MrrAnalytics, MrrWaterfallEntry

ZERO = Decimal("0.00")
CENTS = Decimal("0.01")

# Periods per month, to normalise a per-period amount into monthly recurring revenue.
MONTHLY_FACTOR = {
    BillingPeriod.DAILY: Decimal("30.4375"),
    BillingPeriod.WEEKLY: Decimal("4.345"),
    BillingPeriod.MONTHLY: Decimal("1"),
    BillingPeriod.YEARLY: Decimal("1") / Decimal("12"),
}


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def _recent_months(today: date, count: int = 6) -> list[str]:
    months: list[str] = []
    year, month = today.year, today.month
    for _ in range(count):
        months.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(months))


def _bucket(rows) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for key, value in rows:
        if key is None:
            continue
        label = key.strftime("%Y-%m") if hasattr(key, "strftime") else str(key)[:7]
        out[label] = Decimal(value or 0)
    return out


def mrr_analytics(db: Session, *, today: date | None = None) -> MrrAnalytics:
    today = today or date.today()

    # Current MRR: one row per active subscription (bounded by active count).
    rows = db.execute(
        select(
            Subscription.id,
            Plan.billing_period,
            func.coalesce(func.sum(SubscriptionLine.amount), ZERO),
        )
        .join(Plan, Subscription.plan_id == Plan.id)
        .join(SubscriptionLine, SubscriptionLine.subscription_id == Subscription.id, isouter=True)
        .where(Subscription.status == SubscriptionStatus.ACTIVE)
        .group_by(Subscription.id, Plan.billing_period)
    ).all()

    mrr = ZERO
    for _sub_id, period, total in rows:
        mrr += (total or ZERO) * MONTHLY_FACTOR.get(period, Decimal("1"))
    mrr = _money(mrr)
    active_subscriptions = len(rows)

    active_customers = (
        db.scalar(
            select(func.count(func.distinct(Subscription.customer_id))).where(
                Subscription.status == SubscriptionStatus.ACTIVE
            )
        )
        or 0
    )
    arpu = _money(mrr / active_customers) if active_customers else ZERO
    arr = _money(mrr * 12)

    # First activation per subscription -> New; closures -> Churn.
    first_active = (
        select(
            SubscriptionHistory.subscription_id.label("sid"),
            func.min(SubscriptionHistory.created_at).label("t"),
        )
        .where(SubscriptionHistory.to_status == SubscriptionStatus.ACTIVE)
        .group_by(SubscriptionHistory.subscription_id)
        .subquery()
    )
    # Group by the first selected column (the month) by position, so the SELECT and
    # GROUP BY use the exact same expression on Postgres.
    new_counts = _bucket(
        db.execute(
            select(func.date_trunc("month", first_active.c.t), func.count()).group_by(text("1"))
        ).all()
    )
    churn_counts = _bucket(
        db.execute(
            select(func.date_trunc("month", SubscriptionHistory.created_at), func.count())
            .where(SubscriptionHistory.to_status == SubscriptionStatus.CLOSED)
            .group_by(text("1"))
        ).all()
    )
    expansion = _bucket(
        db.execute(
            select(func.date_trunc("month", ProrationAdjustment.created_at), func.sum(ProrationAdjustment.amount))
            .where(ProrationAdjustment.amount > ZERO)
            .group_by(text("1"))
        ).all()
    )
    contraction = _bucket(
        db.execute(
            select(func.date_trunc("month", ProrationAdjustment.created_at), func.sum(ProrationAdjustment.amount))
            .where(ProrationAdjustment.amount < ZERO)
            .group_by(text("1"))
        ).all()
    )

    waterfall: list[MrrWaterfallEntry] = []
    for month in _recent_months(today):
        new_mrr = _money(Decimal(new_counts.get(month, 0)) * arpu)
        churn_mrr = _money(-(Decimal(churn_counts.get(month, 0)) * arpu))
        exp = _money(expansion.get(month, ZERO))
        con = _money(contraction.get(month, ZERO))
        net = _money(new_mrr + exp + con + churn_mrr)
        waterfall.append(
            MrrWaterfallEntry(month=month, new=new_mrr, expansion=exp, contraction=con, churn=churn_mrr, net=net)
        )

    current_month = today.strftime("%Y-%m")
    churned_this_month = Decimal(churn_counts.get(current_month, 0))
    churn_rate = (
        _money(churned_this_month / active_subscriptions * 100) if active_subscriptions else ZERO
    )

    return MrrAnalytics(
        mrr=mrr,
        arr=arr,
        arpu=arpu,
        active_subscriptions=active_subscriptions,
        active_customers=active_customers,
        churn_rate=churn_rate,
        waterfall=waterfall,
    )

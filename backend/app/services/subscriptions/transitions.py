"""The single place subscription state changes happen.

Every move validates the transition, records a history row and writes an audit entry.
Pause / early-close / renew additionally honour the plan's flags.
"""

import calendar
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.catalog import BillingPeriod, Plan
from app.models.subscriptions import (
    Subscription,
    SubscriptionHistory,
    SubscriptionStatus,
)
from app.services.audit import record_audit

S = SubscriptionStatus

# Allowed forward/lifecycle moves. Anything not listed is rejected.
ALLOWED: dict[SubscriptionStatus, set[SubscriptionStatus]] = {
    S.DRAFT: {S.QUOTATION},
    S.QUOTATION: {S.CONFIRMED, S.DRAFT},
    S.CONFIRMED: {S.ACTIVE, S.CLOSED},
    S.ACTIVE: {S.PAUSED, S.CLOSED},
    S.PAUSED: {S.ACTIVE, S.CLOSED},
    S.CLOSED: {S.ACTIVE},
}


class TransitionError(ValueError):
    """Raised for an illegal transition or an action the plan's flags forbid."""


def _add_months(d: date, months: int) -> date:
    index = d.month - 1 + months
    year = d.year + index // 12
    month = index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def add_period(d: date, period: BillingPeriod) -> date:
    if period is BillingPeriod.DAILY:
        return d + timedelta(days=1)
    if period is BillingPeriod.WEEKLY:
        return d + timedelta(days=7)
    if period is BillingPeriod.MONTHLY:
        return _add_months(d, 1)
    return _add_months(d, 12)  # YEARLY


def _plan(db: Session, sub: Subscription) -> Plan:
    plan = db.get(Plan, sub.plan_id)
    if plan is None:
        raise TransitionError("The subscription's plan no longer exists.")
    return plan


def transition(
    db: Session,
    sub: Subscription,
    to_status: SubscriptionStatus,
    *,
    actor: User | None,
    note: str | None = None,
) -> Subscription:
    if to_status not in ALLOWED.get(sub.status, set()):
        raise TransitionError(
            f"Cannot move a subscription from {sub.status.value} to {to_status.value}."
        )
    from_status = sub.status
    sub.status = to_status
    # Start the billing clock when a confirmed subscription goes live.
    if to_status is S.ACTIVE and from_status is S.CONFIRMED and sub.next_billing_date is None:
        sub.next_billing_date = sub.start_date

    db.add(
        SubscriptionHistory(
            subscription_id=sub.id,
            from_status=from_status,
            to_status=to_status,
            actor_id=actor.id if actor else None,
            note=note,
        )
    )
    record_audit(
        db, actor=actor, entity_type="subscription", entity_id=sub.id, action="transition",
        changes={"from": from_status.value, "to": to_status.value},
    )
    db.flush()
    return sub


# --- Named lifecycle actions ---------------------------------------------------------

def submit(db: Session, sub: Subscription, *, actor: User | None, note: str | None = None):
    return transition(db, sub, S.QUOTATION, actor=actor, note=note)


def confirm(db: Session, sub: Subscription, *, actor: User | None, note: str | None = None):
    return transition(db, sub, S.CONFIRMED, actor=actor, note=note)


def activate(db: Session, sub: Subscription, *, actor: User | None, note: str | None = None):
    return transition(db, sub, S.ACTIVE, actor=actor, note=note)


def pause(db: Session, sub: Subscription, *, actor: User | None, note: str | None = None):
    if sub.status is not S.ACTIVE:
        raise TransitionError("Only an active subscription can be paused.")
    if not _plan(db, sub).allow_pause:
        raise TransitionError("This plan does not allow pausing.")
    return transition(db, sub, S.PAUSED, actor=actor, note=note)


def resume(db: Session, sub: Subscription, *, actor: User | None, note: str | None = None):
    if sub.status is not S.PAUSED:
        raise TransitionError("Only a paused subscription can be resumed.")
    return transition(db, sub, S.ACTIVE, actor=actor, note=note)


def close(db: Session, sub: Subscription, *, actor: User | None, note: str | None = None):
    # Closing while running is an "early close", gated by the plan flag.
    if sub.status in (S.ACTIVE, S.PAUSED) and not _plan(db, sub).allow_early_close:
        raise TransitionError("This plan does not allow closing early.")
    return transition(db, sub, S.CLOSED, actor=actor, note=note)


def renew(db: Session, sub: Subscription, *, actor: User | None, note: str | None = None):
    if sub.status is not S.CLOSED:
        raise TransitionError("Only a closed subscription can be renewed.")
    plan = _plan(db, sub)
    if not plan.allow_renew:
        raise TransitionError("This plan does not allow renewing.")
    sub.expiry_date = add_period(sub.expiry_date, plan.billing_period)
    sub.next_billing_date = date.today()
    return transition(db, sub, S.ACTIVE, actor=actor, note=note)

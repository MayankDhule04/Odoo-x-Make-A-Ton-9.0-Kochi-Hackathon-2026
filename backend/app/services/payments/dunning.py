"""Dunning (#1) and revenue-at-risk (#5).

Dunning schedule: reminder emails at day 1, 3, 5, 7 after an invoice's due date, then
automatic suspension of the subscription once the final reminder has passed.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.billing import Invoice, InvoiceStatus
from app.models.customers import Customer
from app.models.payments import DunningAttempt, DunningKind
from app.models.subscriptions import Subscription, SubscriptionStatus
from app.schemas.payments import (
    DunningRunResponse,
    RevenueAtRiskItem,
    RevenueAtRiskResponse,
)
from app.services.audit import record_audit
from app.services.email import send_email
from app.services.subscriptions.transitions import transition

ZERO = Decimal("0.00")
OPEN_STATES = (InvoiceStatus.DRAFT, InvoiceStatus.CONFIRMED)

# Days after the due date at which reminders go out. Suspension follows the last one.
RETRY_OFFSETS = [1, 3, 5, 7]


def _overdue_invoices(db: Session, today: date) -> list[Invoice]:
    due = Invoice.amount_total - Invoice.amount_paid
    stmt = (
        select(Invoice)
        .where(Invoice.status == InvoiceStatus.CONFIRMED, Invoice.due_date < today, due > ZERO)
        .order_by(Invoice.id)
    )
    return list(db.scalars(stmt))


def _reminder_body(invoice: Invoice, days_overdue: int) -> str:
    due = invoice.amount_total - invoice.amount_paid
    return (
        f"<p>This is a reminder that invoice <strong>{invoice.number}</strong> is "
        f"<strong>{days_overdue} day(s) overdue</strong>.</p>"
        f"<p>Amount due: <strong>INR {due}</strong> (due on {invoice.due_date}).</p>"
        f"<p>Please arrange payment to avoid interruption of your subscription.</p>"
    )


def _send_reminder(db: Session, invoice: Invoice, days_overdue: int) -> None:
    customer = db.get(Customer, invoice.customer_id)
    to = customer.email if customer else "unknown@brightloop.dev"
    send_email(
        db,
        to=to,
        subject=f"Payment reminder: invoice {invoice.number} ({days_overdue} days overdue)",
        body=_reminder_body(invoice, days_overdue),
    )


def _attempt_exists(db: Session, invoice_id: int, *, attempt_number: int | None = None, kind: DunningKind) -> bool:
    stmt = select(DunningAttempt.id).where(
        DunningAttempt.invoice_id == invoice_id, DunningAttempt.kind == kind
    )
    if attempt_number is not None:
        stmt = stmt.where(DunningAttempt.attempt_number == attempt_number)
    return db.scalar(stmt) is not None


def run_dunning(db: Session, as_of_date: date | None = None, *, actor: User | None = None) -> DunningRunResponse:
    today = as_of_date or date.today()
    invoices = _overdue_invoices(db, today)

    reminders_sent = 0
    suspensions = 0

    for invoice in invoices:
        days_overdue = (today - invoice.due_date).days

        # Scheduled reminders, each sent once.
        for step, offset in enumerate(RETRY_OFFSETS, start=1):
            if days_overdue >= offset and not _attempt_exists(
                db, invoice.id, attempt_number=step, kind=DunningKind.REMINDER
            ):
                _send_reminder(db, invoice, days_overdue)
                db.add(
                    DunningAttempt(
                        invoice_id=invoice.id,
                        subscription_id=invoice.subscription_id,
                        attempt_number=step,
                        kind=DunningKind.REMINDER,
                        days_overdue=days_overdue,
                        note=f"Scheduled reminder {step} (day {offset})",
                    )
                )
                reminders_sent += 1

        # Auto-suspend after the final reminder, once only.
        if days_overdue > RETRY_OFFSETS[-1] and not _attempt_exists(
            db, invoice.id, kind=DunningKind.SUSPENSION
        ):
            sub = db.get(Subscription, invoice.subscription_id) if invoice.subscription_id else None
            if sub is not None and sub.status is SubscriptionStatus.ACTIVE:
                # Dunning suspension overrides the plan's pause flag by going through
                # the transition function directly (ACTIVE -> PAUSED is a legal move).
                transition(
                    db, sub, SubscriptionStatus.PAUSED, actor=actor,
                    note=f"Dunning auto-suspension: invoice {invoice.number} unpaid {days_overdue} days",
                )
            db.add(
                DunningAttempt(
                    invoice_id=invoice.id,
                    subscription_id=invoice.subscription_id,
                    attempt_number=len(RETRY_OFFSETS) + 1,
                    kind=DunningKind.SUSPENSION,
                    days_overdue=days_overdue,
                    note="Auto-suspension after final reminder",
                )
            )
            suspensions += 1

    db.flush()
    return DunningRunResponse(
        as_of_date=today,
        invoices_processed=len(invoices),
        reminders_sent=reminders_sent,
        suspensions=suspensions,
    )


def dunning_query(subscription_id: int | None = None, invoice_id: int | None = None):
    stmt = select(DunningAttempt).order_by(DunningAttempt.id.desc())
    if subscription_id is not None:
        stmt = stmt.where(DunningAttempt.subscription_id == subscription_id)
    if invoice_id is not None:
        stmt = stmt.where(DunningAttempt.invoice_id == invoice_id)
    return stmt


def revenue_at_risk(db: Session, today: date | None = None) -> RevenueAtRiskResponse:
    """Overdue subscriptions ranked by amount at risk, with worst days-overdue."""
    today = today or date.today()
    due = Invoice.amount_total - Invoice.amount_paid
    stmt = (
        select(
            Subscription.id,
            Subscription.number,
            Customer.id,
            Customer.name,
            func.coalesce(func.sum(due), ZERO).label("overdue_amount"),
            func.min(Invoice.due_date).label("earliest_due"),
            func.count().label("invoice_count"),
        )
        .join(Subscription, Invoice.subscription_id == Subscription.id)
        .join(Customer, Invoice.customer_id == Customer.id)
        .where(Invoice.status == InvoiceStatus.CONFIRMED, Invoice.due_date < today, due > ZERO)
        .group_by(Subscription.id, Subscription.number, Customer.id, Customer.name)
        .order_by(func.sum(due).desc())
    )

    items: list[RevenueAtRiskItem] = []
    total = ZERO
    for sub_id, sub_number, cust_id, cust_name, amount, earliest_due, count in db.execute(stmt):
        total += amount
        items.append(
            RevenueAtRiskItem(
                subscription_id=sub_id,
                subscription_number=sub_number,
                customer_id=cust_id,
                customer_name=cust_name,
                overdue_amount=amount,
                days_overdue=(today - earliest_due).days,
                invoice_count=count,
            )
        )
    return RevenueAtRiskResponse(total_at_risk=total, items=items)


def send_reminder_for_subscription(
    db: Session, subscription_id: int, *, actor: User | None = None, today: date | None = None
) -> int:
    """One-click reminder: email every overdue invoice of a subscription. Returns count."""
    today = today or date.today()
    due = Invoice.amount_total - Invoice.amount_paid
    invoices = list(
        db.scalars(
            select(Invoice).where(
                Invoice.subscription_id == subscription_id,
                Invoice.status == InvoiceStatus.CONFIRMED,
                Invoice.due_date < today,
                due > ZERO,
            )
        )
    )
    sent = 0
    for invoice in invoices:
        days_overdue = (today - invoice.due_date).days
        _send_reminder(db, invoice, days_overdue)
        db.add(
            DunningAttempt(
                invoice_id=invoice.id,
                subscription_id=subscription_id,
                attempt_number=0,
                kind=DunningKind.REMINDER,
                days_overdue=days_overdue,
                note="Manual reminder",
            )
        )
        sent += 1
    db.flush()
    if actor is not None and sent:
        record_audit(
            db, actor=actor, entity_type="subscription", entity_id=subscription_id,
            action="dunning_reminder", changes={"reminders": sent},
        )
    return sent

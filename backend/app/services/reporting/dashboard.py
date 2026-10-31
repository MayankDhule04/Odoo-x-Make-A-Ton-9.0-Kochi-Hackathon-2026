"""Finance dashboard aggregates and CSV exports. All numbers come from SQL aggregation
(never by loading rows into memory), to stay within the 2-second budget at scale."""

import csv
import io
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.billing import Invoice, InvoiceStatus
from app.models.customers import Customer
from app.models.payments import Payment
from app.models.subscriptions import Subscription, SubscriptionStatus
from app.schemas.reporting import DashboardSummary

ZERO = Decimal("0.00")
OPEN_STATES = (InvoiceStatus.DRAFT, InvoiceStatus.CONFIRMED)


def dashboard_summary(
    db: Session,
    *,
    start: date | None = None,
    end: date | None = None,
    customer_id: int | None = None,
    plan_id: int | None = None,
    today: date | None = None,
) -> DashboardSummary:
    today = today or date.today()
    due = Invoice.amount_total - Invoice.amount_paid

    # Active subscriptions (optionally filtered by plan / customer).
    sub_q = select(func.count()).select_from(Subscription).where(
        Subscription.status == SubscriptionStatus.ACTIVE
    )
    if plan_id is not None:
        sub_q = sub_q.where(Subscription.plan_id == plan_id)
    if customer_id is not None:
        sub_q = sub_q.where(Subscription.customer_id == customer_id)
    active_subscriptions = db.scalar(sub_q) or 0

    # Revenue collected (payments) within the optional date window.
    rev_q = select(func.coalesce(func.sum(Payment.amount), ZERO))
    if start is not None:
        rev_q = rev_q.where(Payment.paid_at >= start)
    if end is not None:
        rev_q = rev_q.where(Payment.paid_at <= end)
    if customer_id is not None:
        rev_q = rev_q.where(Payment.customer_id == customer_id)
    revenue_collected = db.scalar(rev_q) or ZERO

    # Amount owed across open invoices.
    owed_q = select(func.coalesce(func.sum(due), ZERO)).where(
        Invoice.status.in_(OPEN_STATES), due > ZERO
    )
    if customer_id is not None:
        owed_q = owed_q.where(Invoice.customer_id == customer_id)
    amount_owed = db.scalar(owed_q) or ZERO

    # Overdue.
    overdue_base = select(Invoice).where(
        Invoice.status.in_(OPEN_STATES), due > ZERO, Invoice.due_date < today
    )
    if customer_id is not None:
        overdue_base = overdue_base.where(Invoice.customer_id == customer_id)
    overdue_count = db.scalar(select(func.count()).select_from(overdue_base.subquery())) or 0
    overdue_amount_q = select(func.coalesce(func.sum(due), ZERO)).where(
        Invoice.status.in_(OPEN_STATES), due > ZERO, Invoice.due_date < today
    )
    if customer_id is not None:
        overdue_amount_q = overdue_amount_q.where(Invoice.customer_id == customer_id)
    overdue_amount = db.scalar(overdue_amount_q) or ZERO

    customers = db.scalar(select(func.count()).select_from(Customer)) or 0

    return DashboardSummary(
        active_subscriptions=active_subscriptions,
        revenue_collected=revenue_collected,
        amount_owed=amount_owed,
        overdue_count=overdue_count,
        overdue_amount=overdue_amount,
        customers=customers,
    )


def invoices_csv(db: Session, *, status: InvoiceStatus | None = None, customer_id: int | None = None) -> str:
    query = (
        select(
            Invoice.number,
            Invoice.status,
            Invoice.issue_date,
            Invoice.due_date,
            Invoice.amount_total,
            Invoice.amount_paid,
            (Invoice.amount_total - Invoice.amount_paid).label("amount_due"),
            Customer.name,
        )
        .join(Customer, Invoice.customer_id == Customer.id)
        .order_by(Invoice.id)
    )
    if status is not None:
        query = query.where(Invoice.status == status)
    if customer_id is not None:
        query = query.where(Invoice.customer_id == customer_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["number", "status", "issue_date", "due_date", "total", "paid", "due", "customer"])
    for row in db.execute(query):
        number, st, issue, due_d, total, paid, amt_due, cust = row
        writer.writerow([
            number,
            st.value if hasattr(st, "value") else st,
            issue, due_d, total, paid, amt_due, cust,
        ])
    return buffer.getvalue()


def payments_csv(db: Session, *, customer_id: int | None = None) -> str:
    query = (
        select(Payment.id, Payment.invoice_id, Payment.amount, Payment.method, Payment.paid_at, Customer.name)
        .join(Customer, Payment.customer_id == Customer.id)
        .order_by(Payment.id)
    )
    if customer_id is not None:
        query = query.where(Payment.customer_id == customer_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "invoice_id", "amount", "method", "paid_at", "customer"])
    for pid, inv_id, amount, method, paid_at, cust in db.execute(query):
        writer.writerow([pid, inv_id, amount, method.value if hasattr(method, "value") else method, paid_at, cust])
    return buffer.getvalue()

"""Billing engine: transactional, idempotent recurring billing runs.

Contract:
- Unique constraint on (subscription_id, period_start, period_end)
- Advances next_billing_date in the SAME transaction
- Re-run on the same day creates 0 duplicates
- Crash mid-run is safely resumable
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.billing import Invoice, InvoiceLine, InvoiceStatus
from app.models.catalog import Plan
from app.models.subscriptions import PaymentTerms, Subscription, SubscriptionStatus
from app.services.audit import record_audit
from app.services.billing.calculator import calculate_subscription_invoice
from app.services.billing.invoices import _next_invoice_number
from app.services.subscriptions.transitions import add_period

ZERO = Decimal("0.00")


@dataclass
class BillingRunResult:
    as_of_date: date
    created_count: int
    skipped_count: int
    total_amount: Decimal
    invoices: list[Invoice]


def calculate_due_date(period_start: date, terms: PaymentTerms) -> date:
    """Calculate invoice due date according to subscription payment terms."""
    if terms == PaymentTerms.NET_15:
        return period_start + timedelta(days=15)
    if terms == PaymentTerms.NET_30:
        return period_start + timedelta(days=30)
    return period_start  # IMMEDIATE


def run_billing(
    db: Session,
    as_of_date: date | None = None,
    *,
    actor: User | None = None,
) -> BillingRunResult:
    """Run recurring billing for all active subscriptions due on or before as_of_date.

    Idempotent and atomic:
    - Avoids duplicate billing via the unique (subscription_id, period_start, period_end)
    - Advances next_billing_date in the same transaction
    """
    as_of = as_of_date or date.today()

    # Query all ACTIVE subscriptions due for billing
    query = (
        select(Subscription)
        .where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.next_billing_date.isnot(None),
            Subscription.next_billing_date <= as_of,
        )
        .order_by(Subscription.id)
    )
    due_subs = list(db.scalars(query).all())

    created_invoices: list[Invoice] = []
    skipped_count = 0
    total_revenue = ZERO

    for sub in due_subs:
        plan = db.get(Plan, sub.plan_id)
        if plan is None:
            skipped_count += 1
            continue

        period_start = sub.next_billing_date
        next_billing = add_period(period_start, plan.billing_period)
        period_end = next_billing - timedelta(days=1)

        # Idempotency check: check if an invoice already exists for this exact period
        existing = db.scalar(
            select(Invoice).where(
                Invoice.subscription_id == sub.id,
                Invoice.period_start == period_start,
                Invoice.period_end == period_end,
            )
        )
        if existing is not None:
            # Advance next_billing_date if needed to heal state, and skip
            if sub.next_billing_date == period_start:
                sub.next_billing_date = next_billing
                db.flush()
            skipped_count += 1
            continue

        due_date = calculate_due_date(period_start, sub.payment_terms)
        calc_res = calculate_subscription_invoice(db, sub, period_start)

        year = period_start.year
        seq_id, number = _next_invoice_number(db, year)

        invoice = Invoice(
            id=seq_id,
            number=number,
            customer_id=sub.customer_id,
            subscription_id=sub.id,
            status=InvoiceStatus.CONFIRMED,  # Automatically confirmed upon billing run
            issue_date=as_of,
            due_date=due_date,
            period_start=period_start,
            period_end=period_end,
            amount_subtotal=calc_res.amount_subtotal,
            amount_tax=calc_res.amount_tax,
            amount_discount=calc_res.amount_discount,
            amount_total=calc_res.amount_total,
            amount_paid=ZERO,
            notes=f"Recurring billing for {sub.number} ({period_start} to {period_end})",
        )

        for line in calc_res.lines:
            invoice.lines.append(
                InvoiceLine(
                    description=line.description,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    product_id=line.product_id,
                    variant_id=line.variant_id,
                    tax_id=line.tax_id,
                    tax_rate=line.tax_rate,
                    tax_amount=line.tax_amount,
                    discount_amount=line.discount_amount,
                    amount=line.amount,
                    line_type=line.line_type,
                )
            )

        db.add(invoice)

        # Record discount usage and increment counters
        from app.models.billing import DiscountUsage
        for discount, applied_amt in calc_res.applied_discounts:
            discount.usage_count += 1
            db.add(
                DiscountUsage(
                    discount_id=discount.id,
                    invoice_id=invoice.id,
                    customer_id=sub.customer_id,
                    amount_applied=applied_amt,
                )
            )

        # Advance next_billing_date in the SAME transaction!
        if plan.auto_close and next_billing > sub.expiry_date:
            sub.next_billing_date = None
            sub.status = SubscriptionStatus.CLOSED
        else:
            sub.next_billing_date = next_billing

        db.flush()

        record_audit(
            db,
            actor=actor,
            entity_type="invoice",
            entity_id=invoice.id,
            action="billing_run_generate",
            changes={
                "number": invoice.number,
                "subscription_id": sub.id,
                "period": f"{period_start} to {period_end}",
                "amount": str(invoice.amount_total),
            },
        )

        created_invoices.append(invoice)
        total_revenue += invoice.amount_total

    return BillingRunResult(
        as_of_date=as_of,
        created_count=len(created_invoices),
        skipped_count=skipped_count,
        total_amount=total_revenue,
        invoices=created_invoices,
    )


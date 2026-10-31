"""Dry-run billing preview with exceptions queue (Differentiator #4).

Inspects upcoming recurring subscriptions and highlights anomalies, missing configurations,
or expired plans before real money moves.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Plan, Product, Tax
from app.models.customers import Customer
from app.models.subscriptions import Subscription, SubscriptionStatus
from app.schemas.billing import (
    DryRunExceptionItem,
    DryRunInvoiceItem,
    DryRunResponse,
)
from app.services.billing.calculator import calculate_subscription_invoice
from app.services.billing.engine import calculate_due_date
from app.services.subscriptions.transitions import add_period

ZERO = Decimal("0.00")


def preview_billing_run(
    db: Session,
    as_of_date: date | None = None,
) -> DryRunResponse:
    """Generate a read-only preview of what the billing run will create,

    including an exceptions queue for subscriptions that require attention.
    """
    as_of = as_of_date or date.today()

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

    projected_invoices: list[DryRunInvoiceItem] = []
    exceptions: list[DryRunExceptionItem] = []
    projected_total = ZERO

    for sub in due_subs:
        customer = db.get(Customer, sub.customer_id)
        plan = db.get(Plan, sub.plan_id)
        cust_name = customer.name if customer else f"Customer #{sub.customer_id}"

        # 1. Check for missing customer or inactive customer
        if customer is None:
            exceptions.append(
                DryRunExceptionItem(
                    subscription_id=sub.id,
                    subscription_number=sub.number,
                    customer_id=sub.customer_id,
                    customer_name=cust_name,
                    error_code="CUSTOMER_NOT_FOUND",
                    severity="BLOCKER",
                    message="Referenced customer record was deleted or does not exist.",
                    recommendation="Reassign subscription to a valid customer.",
                )
            )
            continue

        if not customer.is_active:
            exceptions.append(
                DryRunExceptionItem(
                    subscription_id=sub.id,
                    subscription_number=sub.number,
                    customer_id=sub.customer_id,
                    customer_name=cust_name,
                    error_code="INACTIVE_CUSTOMER",
                    severity="BLOCKER",
                    message=f"Customer '{customer.name}' is marked inactive.",
                    recommendation="Reactivate customer profile or pause/close the subscription.",
                )
            )
            continue

        if not customer.email:
            exceptions.append(
                DryRunExceptionItem(
                    subscription_id=sub.id,
                    subscription_number=sub.number,
                    customer_id=sub.customer_id,
                    customer_name=cust_name,
                    error_code="MISSING_EMAIL",
                    severity="WARNING",
                    message="Customer has no billing email address configured.",
                    recommendation="Add an email address to customer profile so invoice can be sent.",
                )
            )

        # 2. Check plan validity
        if plan is None:
            exceptions.append(
                DryRunExceptionItem(
                    subscription_id=sub.id,
                    subscription_number=sub.number,
                    customer_id=sub.customer_id,
                    customer_name=cust_name,
                    error_code="PLAN_NOT_FOUND",
                    severity="BLOCKER",
                    message=f"Plan #{sub.plan_id} no longer exists.",
                    recommendation="Update subscription to an active plan.",
                )
            )
            continue

        period_start = sub.next_billing_date
        next_billing = add_period(period_start, plan.billing_period)
        period_end = next_billing - timedelta(days=1)

        if not plan.is_available_on(period_start):
            exceptions.append(
                DryRunExceptionItem(
                    subscription_id=sub.id,
                    subscription_number=sub.number,
                    customer_id=sub.customer_id,
                    customer_name=cust_name,
                    error_code="EXPIRED_PLAN",
                    severity="WARNING",
                    message=f"Plan '{plan.name}' is outside its availability window ({plan.available_from} to {plan.available_to}).",
                    recommendation="Extend plan availability window or migrate customer to a new plan.",
                )
            )

        # 3. Check subscription expiry
        if sub.expiry_date < sub.next_billing_date:
            exceptions.append(
                DryRunExceptionItem(
                    subscription_id=sub.id,
                    subscription_number=sub.number,
                    customer_id=sub.customer_id,
                    customer_name=cust_name,
                    error_code="PAST_EXPIRY",
                    severity="BLOCKER",
                    message=f"Subscription expired on {sub.expiry_date} before next billing date {sub.next_billing_date}.",
                    recommendation="Renew the subscription or close it.",
                )
            )
            continue

        # 4. Check subscription lines
        if not sub.lines:
            exceptions.append(
                DryRunExceptionItem(
                    subscription_id=sub.id,
                    subscription_number=sub.number,
                    customer_id=sub.customer_id,
                    customer_name=cust_name,
                    error_code="EMPTY_LINES",
                    severity="BLOCKER",
                    message="Subscription has no product lines.",
                    recommendation="Add product lines before generating an invoice.",
                )
            )
            continue

        # 5. Check missing taxes or products
        has_blocker_line = False
        for line in sub.lines:
            if line.product_id and db.get(Product, line.product_id) is None:
                exceptions.append(
                    DryRunExceptionItem(
                        subscription_id=sub.id,
                        subscription_number=sub.number,
                        customer_id=sub.customer_id,
                        customer_name=cust_name,
                        error_code="PRODUCT_NOT_FOUND",
                        severity="BLOCKER",
                        message=f"Referenced product #{line.product_id} no longer exists.",
                        recommendation="Update subscription line with an active product.",
                    )
                )
                has_blocker_line = True
                break

            if line.tax_id and db.get(Tax, line.tax_id) is None:
                exceptions.append(
                    DryRunExceptionItem(
                        subscription_id=sub.id,
                        subscription_number=sub.number,
                        customer_id=sub.customer_id,
                        customer_name=cust_name,
                        error_code="MISSING_TAX",
                        severity="WARNING",
                        message=f"Referenced tax rule #{line.tax_id} was deleted.",
                        recommendation="Assign a valid tax rule to the line.",
                    )
                )

        if has_blocker_line:
            continue

        # Compute projected invoice
        due_date = calculate_due_date(period_start, sub.payment_terms)
        calc_res = calculate_subscription_invoice(db, sub, period_start)

        projected_invoices.append(
            DryRunInvoiceItem(
                subscription_id=sub.id,
                subscription_number=sub.number,
                customer_id=sub.customer_id,
                customer_name=cust_name,
                period_start=period_start,
                period_end=period_end,
                due_date=due_date,
                amount_subtotal=calc_res.amount_subtotal,
                amount_tax=calc_res.amount_tax,
                amount_discount=calc_res.amount_discount,
                amount_total=calc_res.amount_total,
                lines_count=len(calc_res.lines),
            )
        )
        projected_total += calc_res.amount_total

    return DryRunResponse(
        as_of_date=as_of,
        projected_invoices_count=len(projected_invoices),
        projected_total_amount=projected_total,
        exceptions_count=len(exceptions),
        projected_invoices=projected_invoices,
        exceptions=exceptions,
    )


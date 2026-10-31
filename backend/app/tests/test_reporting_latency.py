"""Latency budget: dashboard and MRR stay well under 2 seconds at scale.

Bulk-loads a sizeable dataset with core inserts, then times the aggregation services
directly (SQL aggregation, no row loading). Volumes are large enough to be meaningful
while keeping the test runtime reasonable in CI.
"""

import time
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.models.billing import Invoice, InvoiceStatus
from app.models.catalog import BillingPeriod, Plan, Product, ProductType
from app.models.customers import Customer
from app.models.payments import Payment, PaymentMethod
from app.models.subscriptions import (
    PaymentTerms,
    Subscription,
    SubscriptionLine,
    SubscriptionStatus,
)
from app.services import reporting as reporting_service

N_CUSTOMERS = 400
N_SUBSCRIPTIONS = 2000
N_INVOICES = 8000
N_PAYMENTS = 4000
BUDGET_SECONDS = 2.0


def _bulk_load(db: Session) -> None:
    today = date.today()

    product = Product(name="Load Product", type=ProductType.SOFTWARE,
                      sales_price=Decimal("1000.00"), cost_price=Decimal("100.00"))
    plan = Plan(name="Load Plan", price=Decimal("1000.00"), billing_period=BillingPeriod.MONTHLY,
                available_from=today - timedelta(days=30), available_to=today + timedelta(days=365))
    db.add_all([product, plan])
    db.flush()

    db.execute(
        insert(Customer.__table__),
        [{"id": i, "name": f"Customer {i}", "email": f"load{i}@example.com"} for i in range(1, N_CUSTOMERS + 1)],
    )
    db.execute(
        insert(Subscription.__table__),
        [
            {
                "id": i,
                "number": f"SUB-2026-{i:06d}",
                "customer_id": (i % N_CUSTOMERS) + 1,
                "plan_id": plan.id,
                "start_date": today - timedelta(days=15),
                "expiry_date": today + timedelta(days=30),
                "next_billing_date": today + timedelta(days=15),
                "payment_terms": PaymentTerms.IMMEDIATE,
                "status": SubscriptionStatus.ACTIVE,
            }
            for i in range(1, N_SUBSCRIPTIONS + 1)
        ],
    )
    db.execute(
        insert(SubscriptionLine.__table__),
        [
            {
                "id": i,
                "subscription_id": i,
                "product_id": product.id,
                "quantity": 1,
                "unit_price": Decimal("1000.00"),
                "amount": Decimal("1000.00"),
            }
            for i in range(1, N_SUBSCRIPTIONS + 1)
        ],
    )
    db.execute(
        insert(Invoice.__table__),
        [
            {
                "id": i,
                "number": f"INV-2026-{i:06d}",
                "customer_id": (i % N_CUSTOMERS) + 1,
                "subscription_id": (i % N_SUBSCRIPTIONS) + 1,
                "status": InvoiceStatus.CONFIRMED,
                "issue_date": today - timedelta(days=10),
                "due_date": today - timedelta(days=1) if i % 3 == 0 else today + timedelta(days=10),
                "amount_subtotal": Decimal("1000.00"),
                "amount_total": Decimal("1000.00"),
                "amount_paid": Decimal("0.00"),
            }
            for i in range(1, N_INVOICES + 1)
        ],
    )
    db.execute(
        insert(Payment.__table__),
        [
            {
                "id": i,
                "invoice_id": (i % N_INVOICES) + 1,
                "customer_id": (i % N_CUSTOMERS) + 1,
                "amount": Decimal("500.00"),
                "method": PaymentMethod.UPI,
                "paid_at": today - timedelta(days=5),
            }
            for i in range(1, N_PAYMENTS + 1)
        ],
    )
    db.flush()


def test_dashboard_and_mrr_within_budget(db_session: Session) -> None:
    _bulk_load(db_session)

    start = time.perf_counter()
    summary = reporting_service.dashboard_summary(db_session)
    dashboard_seconds = time.perf_counter() - start

    start = time.perf_counter()
    mrr = reporting_service.mrr_analytics(db_session)
    mrr_seconds = time.perf_counter() - start

    assert summary.active_subscriptions == N_SUBSCRIPTIONS
    assert Decimal(mrr.mrr) > 0
    assert dashboard_seconds < BUDGET_SECONDS, f"dashboard took {dashboard_seconds:.3f}s"
    assert mrr_seconds < BUDGET_SECONDS, f"mrr took {mrr_seconds:.3f}s"

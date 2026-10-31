"""Integration tests for invoice API routes, RBAC, scoping, and email sending."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth.email_outbox import EmailOutbox
from app.models.billing import Invoice, InvoiceLine, InvoiceStatus
from app.models.catalog import BillingPeriod, Plan, Product
from app.models.customers import Customer
from app.models.subscriptions import PaymentTerms, Subscription, SubscriptionLine, SubscriptionStatus


def _seed_test_invoice(db_session: Session, customer_id: int, number: str = "INV-2026-999001") -> Invoice:
    today = date.today()
    invoice = Invoice(
        number=number,
        customer_id=customer_id,
        status=InvoiceStatus.DRAFT,
        issue_date=today,
        due_date=today + timedelta(days=15),
        amount_subtotal=Decimal("1000.00"),
        amount_tax=Decimal("180.00"),
        amount_discount=Decimal("0.00"),
        amount_total=Decimal("1180.00"),
        amount_paid=Decimal("0.00"),
    )
    invoice.lines.append(
        InvoiceLine(
            description="Consulting Services",
            quantity=1,
            unit_price=Decimal("1000.00"),
            tax_rate=Decimal("18.000"),
            tax_amount=Decimal("180.00"),
            amount=Decimal("1180.00"),
        )
    )
    db_session.add(invoice)
    db_session.flush()
    return invoice


def test_anonymous_access_blocked(client: TestClient):
    """Anonymous visitors receive 401 Unauthorized for billing endpoints."""
    res = client.get("/api/billing/invoices")
    assert res.status_code == 401
    res2 = client.get("/api/invoices")
    assert res2.status_code == 401


def test_customer_invoice_scoping(
    db_session: Session,
    customer_client: TestClient,
    customer_user,
    staff_client: TestClient,
    make_user,
):
    """Customer sees only their own invoices; staff sees all."""
    # Customer 1
    c1 = db_session.scalar(select(Customer).where(Customer.user_id == customer_user.id))
    inv1 = _seed_test_invoice(db_session, c1.id, "INV-2026-000010")

    # Customer 2
    u2 = make_user()
    c2 = db_session.scalar(select(Customer).where(Customer.user_id == u2.id))
    inv2 = _seed_test_invoice(db_session, c2.id, "INV-2026-000020")

    # Customer 1 lists invoices: only sees inv1
    res = customer_client.get("/api/billing/invoices")
    assert res.status_code == 200
    numbers = [item["number"] for item in res.json()["items"]]
    assert "INV-2026-000010" in numbers
    assert "INV-2026-000020" not in numbers

    # Also test via /api/invoices
    res_direct = customer_client.get("/api/invoices")
    assert res_direct.status_code == 200
    direct_numbers = [item["number"] for item in res_direct.json()["items"]]
    assert "INV-2026-000010" in direct_numbers

    # Customer 1 tries to access Customer 2's invoice directly: gets 404
    res = customer_client.get(f"/api/billing/invoices/{inv2.id}")
    assert res.status_code == 404

    # Staff lists invoices: sees both
    staff_res = staff_client.get("/api/billing/invoices")
    assert staff_res.status_code == 200
    staff_numbers = [item["number"] for item in staff_res.json()["items"]]
    assert "INV-2026-000010" in staff_numbers
    assert "INV-2026-000020" in staff_numbers


def test_confirm_and_cancel_invoice_rbac(
    db_session: Session,
    customer_client: TestClient,
    staff_client: TestClient,
    customer_user,
):
    """Staff can confirm and cancel; customer cannot (403)."""
    c = db_session.scalar(select(Customer).where(Customer.user_id == customer_user.id))
    inv = _seed_test_invoice(db_session, c.id, "INV-2026-000030")

    # Customer tries to confirm: 403 Forbidden
    res = customer_client.post(f"/api/billing/invoices/{inv.id}/confirm")
    assert res.status_code == 403

    # Staff confirms: 200 OK
    res = staff_client.post(f"/api/billing/invoices/{inv.id}/confirm")
    assert res.status_code == 200
    assert res.json()["status"] == "CONFIRMED"

    # Staff cancels: 200 OK
    res = staff_client.post(f"/api/billing/invoices/{inv.id}/cancel", json={"note": "Customer requested change"})
    assert res.status_code == 200
    assert res.json()["status"] == "CANCELLED"


def test_send_invoice_adds_to_email_outbox(
    db_session: Session,
    staff_client: TestClient,
    customer_user,
):
    """Sending an invoice adds an entry to EmailOutbox."""
    c = db_session.scalar(select(Customer).where(Customer.user_id == customer_user.id))
    inv = _seed_test_invoice(db_session, c.id, "INV-2026-000040")

    res = staff_client.post(f"/api/billing/invoices/{inv.id}/send")
    assert res.status_code == 200
    assert "sent" in res.json()["message"]

    outbox = db_session.scalar(
        select(EmailOutbox)
        .where(EmailOutbox.to_email == c.email)
        .order_by(EmailOutbox.id.desc())
    )
    assert outbox is not None
    assert inv.number in outbox.subject


def test_render_invoice_html(
    db_session: Session,
    customer_client: TestClient,
    customer_user,
):
    """Invoice render endpoint returns printable HTML layout."""
    c = db_session.scalar(select(Customer).where(Customer.user_id == customer_user.id))
    inv = _seed_test_invoice(db_session, c.id, "INV-2026-000050")

    res = customer_client.get(f"/api/billing/invoices/{inv.id}/render")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Brightloop Subscriptions" in res.text
    assert inv.number in res.text


def test_dry_run_and_run_billing_api(
    db_session: Session,
    staff_client: TestClient,
    customer_client: TestClient,
    customer_user,
):
    """Staff can preview dry run and execute billing runs via API; customer cannot."""
    today = date.today()
    c = db_session.scalar(select(Customer).where(Customer.user_id == customer_user.id))

    plan = Plan(
        name="API Test Plan",
        price=Decimal("1200.00"),
        billing_period=BillingPeriod.MONTHLY,
        available_from=today - timedelta(days=30),
        available_to=today + timedelta(days=365),
    )
    product = Product(name="API Item", sales_price=Decimal("1200.00"), cost_price=Decimal("600.00"))
    db_session.add_all([plan, product])
    db_session.flush()

    sub = Subscription(
        number="SUB-API-001",
        customer_id=c.id,
        plan_id=plan.id,
        start_date=today - timedelta(days=30),
        expiry_date=today + timedelta(days=335),
        next_billing_date=today,
        payment_terms=PaymentTerms.NET_15,
        status=SubscriptionStatus.ACTIVE,
    )
    sub.lines.append(
        SubscriptionLine(product_id=product.id, quantity=1, unit_price=Decimal("1200.00"), amount=Decimal("1200.00"))
    )
    db_session.add(sub)
    db_session.flush()

    # Customer tries to dry-run: 403
    res_cust = customer_client.post("/api/billing/dry-run", json={})
    assert res_cust.status_code == 403

    # Staff dry-run: 200
    res_dry = staff_client.post("/api/billing/dry-run", json={"as_of_date": str(today)})
    assert res_dry.status_code == 200
    data_dry = res_dry.json()
    assert data_dry["projected_invoices_count"] >= 1
    assert data_dry["projected_invoices"][0]["subscription_number"] == "SUB-API-001"

    # Staff runs billing: 200
    res_run = staff_client.post("/api/billing/run", json={"as_of_date": str(today)})
    assert res_run.status_code == 200
    data_run = res_run.json()
    assert data_run["created_count"] >= 1

    # Second run immediately creates 0 duplicates
    res_run2 = staff_client.post("/api/billing/run", json={"as_of_date": str(today)})
    assert res_run2.status_code == 200
    assert res_run2.json()["created_count"] == 0

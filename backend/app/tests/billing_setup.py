"""Shared setup for payment/dunning tests: produce a CONFIRMED invoice via the billing run.

Not named test_* so pytest does not collect it as a test module.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient


def billed_invoice(
    admin_client: TestClient,
    *,
    customer_id: int | None = None,
    start_offset_days: int = 0,
    expiry_offset_days: int = 60,
) -> tuple[dict, int, int]:
    """Create an active subscription and run billing, returning (invoice, subscription_id, customer_id).

    With start_offset_days > 0 the invoice's due date (IMMEDIATE terms) lands in the past,
    making it overdue — handy for dunning tests.
    """
    today = date.today()
    product = admin_client.post(
        "/api/products",
        json={"name": "Pro", "type": "SOFTWARE", "sales_price": "1000.00", "cost_price": "100.00"},
    ).json()
    plan = admin_client.post(
        "/api/plans",
        json={
            "name": "Monthly",
            "price": "1000.00",
            "billing_period": "MONTHLY",
            "available_from": (today - timedelta(days=90)).isoformat(),
            "available_to": (today + timedelta(days=365)).isoformat(),
        },
    ).json()
    if customer_id is None:
        customer_id = admin_client.post(
            "/api/customers", json={"name": "Acme", "email": "acme@example.com"}
        ).json()["id"]

    start = today - timedelta(days=start_offset_days)
    sub = admin_client.post(
        "/api/subscriptions",
        json={
            "customer_id": customer_id,
            "plan_id": plan["id"],
            "start_date": start.isoformat(),
            "expiry_date": (today + timedelta(days=expiry_offset_days)).isoformat(),
            "payment_terms": "IMMEDIATE",
            "lines": [{"product_id": product["id"], "quantity": 1}],
        },
    ).json()
    sid = sub["id"]
    admin_client.post(f"/api/subscriptions/{sid}/submit", json={})
    admin_client.post(f"/api/subscriptions/{sid}/confirm", json={})
    admin_client.post(f"/api/subscriptions/{sid}/activate", json={})

    run = admin_client.post("/api/billing/run", json={"as_of_date": today.isoformat()})
    assert run.status_code == 200, run.text
    body = run.json()
    assert body["created_count"] == 1, body
    return body["invoices"][0], sid, customer_id


def overdue_invoice(
    admin_client: TestClient,
    *,
    days_overdue: int = 20,
    customer_id: int | None = None,
) -> tuple[dict, int, int]:
    """Create an ACTIVE subscription plus a CONFIRMED invoice whose due date is in the
    past, returning (invoice, subscription_id, customer_id).

    Built directly (not via the billing run) because the billing engine stamps today's
    issue_date, and an invoice must have due_date >= issue_date.
    """
    today = date.today()
    product = admin_client.post(
        "/api/products",
        json={"name": "Pro", "type": "SOFTWARE", "sales_price": "1000.00", "cost_price": "100.00"},
    ).json()
    plan = admin_client.post(
        "/api/plans",
        json={
            "name": "Monthly",
            "price": "1000.00",
            "billing_period": "MONTHLY",
            "available_from": (today - timedelta(days=90)).isoformat(),
            "available_to": (today + timedelta(days=365)).isoformat(),
        },
    ).json()
    if customer_id is None:
        customer_id = admin_client.post(
            "/api/customers", json={"name": "Acme", "email": "acme@example.com"}
        ).json()["id"]

    sub = admin_client.post(
        "/api/subscriptions",
        json={
            "customer_id": customer_id,
            "plan_id": plan["id"],
            "start_date": today.isoformat(),
            "expiry_date": (today + timedelta(days=60)).isoformat(),
            "payment_terms": "IMMEDIATE",
            "lines": [{"product_id": product["id"], "quantity": 1}],
        },
    ).json()
    sid = sub["id"]
    admin_client.post(f"/api/subscriptions/{sid}/submit", json={})
    admin_client.post(f"/api/subscriptions/{sid}/confirm", json={})
    admin_client.post(f"/api/subscriptions/{sid}/activate", json={})

    created = admin_client.post(
        "/api/invoices",
        json={
            "customer_id": customer_id,
            "subscription_id": sid,
            "issue_date": (today - timedelta(days=days_overdue + 5)).isoformat(),
            "due_date": (today - timedelta(days=days_overdue)).isoformat(),
            "lines": [
                {"description": "Subscription charge", "quantity": 1, "unit_price": "1000.00", "amount": "1000.00"}
            ],
        },
    )
    assert created.status_code == 201, created.text
    iid = created.json()["id"]
    confirmed = admin_client.post(f"/api/invoices/{iid}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    return confirmed.json(), sid, customer_id

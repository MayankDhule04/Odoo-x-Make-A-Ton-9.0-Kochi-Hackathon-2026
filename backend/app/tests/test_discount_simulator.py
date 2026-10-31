"""Discount simulator (differentiator #6): reach and projected monthly impact."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient


def _one_active_subscription(admin_client: TestClient) -> int:
    """Create a single ACTIVE monthly subscription worth 1000 and return its product id."""
    product = admin_client.post(
        "/api/products",
        json={"name": "Pro", "type": "SOFTWARE", "sales_price": "1000.00", "cost_price": "100.00"},
    ).json()
    today = date.today()
    plan = admin_client.post(
        "/api/plans",
        json={
            "name": "Monthly",
            "price": "1000.00",
            "billing_period": "MONTHLY",
            "available_from": (today - timedelta(days=5)).isoformat(),
            "available_to": (today + timedelta(days=365)).isoformat(),
        },
    ).json()
    customer = admin_client.post("/api/customers", json={"name": "Acme", "email": "a@example.com"}).json()
    sub = admin_client.post(
        "/api/subscriptions",
        json={
            "customer_id": customer["id"],
            "plan_id": plan["id"],
            "start_date": today.isoformat(),
            "expiry_date": (today + timedelta(days=60)).isoformat(),
            "lines": [{"product_id": product["id"], "quantity": 1}],
        },
    ).json()
    sid = sub["id"]
    admin_client.post(f"/api/subscriptions/{sid}/submit", json={})
    admin_client.post(f"/api/subscriptions/{sid}/confirm", json={})
    admin_client.post(f"/api/subscriptions/{sid}/activate", json={})
    return product["id"]


def test_percentage_discount_reach_and_impact(admin_client: TestClient) -> None:
    _one_active_subscription(admin_client)

    resp = admin_client.post(
        "/api/discounts/simulate",
        json={"type": "PERCENTAGE", "value": "10.00", "target": "SUBSCRIPTION"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["active_subscriptions"] == 1
    assert body["matched_count"] == 1
    # 10% of a 1000 monthly subscription = 100/month.
    assert Decimal(body["projected_monthly_impact"]) == Decimal("100.00")


def test_min_purchase_excludes_subscriptions(admin_client: TestClient) -> None:
    _one_active_subscription(admin_client)
    resp = admin_client.post(
        "/api/discounts/simulate",
        json={
            "type": "PERCENTAGE",
            "value": "10.00",
            "target": "SUBSCRIPTION",
            "min_purchase_amount": "5000.00",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["matched_count"] == 0


def test_simulate_is_admin_only(staff_client: TestClient) -> None:
    resp = staff_client.post(
        "/api/discounts/simulate",
        json={"type": "PERCENTAGE", "value": "10.00", "target": "SUBSCRIPTION"},
    )
    assert resp.status_code == 403

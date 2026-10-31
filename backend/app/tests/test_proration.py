"""Proration (differentiator #2): mid-cycle change produces credit/charge lines."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.subscriptions import Subscription


def _active_subscription(admin_client: TestClient) -> tuple[int, int]:
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
    return sid, product["id"]


def test_preview_then_apply_change(admin_client: TestClient, db_session: Session) -> None:
    sid, pid = _active_subscription(admin_client)

    # Put the subscription mid-cycle: next billing 15 days out (monthly period).
    sub = db_session.get(Subscription, sid)
    sub.next_billing_date = date.today() + timedelta(days=15)
    db_session.flush()

    # Preview doubling the quantity (1000 -> 2000).
    preview = admin_client.post(
        f"/api/subscriptions/{sid}/change/preview",
        json={"lines": [{"product_id": pid, "quantity": 2}]},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert Decimal(body["old_total"]) == Decimal("1000.00")
    assert Decimal(body["new_total"]) == Decimal("2000.00")
    assert Decimal(body["credit"]) < 0  # refund unused part of old
    assert Decimal(body["charge"]) > 0  # charge new config for remaining
    # net = credit + charge, and is a fraction of the 1000 difference.
    net = Decimal(body["net"])
    assert net == (Decimal(body["credit"]) + Decimal(body["charge"]))
    assert Decimal("0.00") < net < Decimal("1000.00")

    # Apply it.
    applied = admin_client.post(
        f"/api/subscriptions/{sid}/change",
        json={"lines": [{"product_id": pid, "quantity": 2}]},
    )
    assert applied.status_code == 200, applied.text
    result = applied.json()
    assert len(result["adjustments"]) == 2  # one credit, one charge

    # Lines updated.
    detail = admin_client.get(f"/api/subscriptions/{sid}").json()
    assert detail["lines"][0]["quantity"] == 2
    assert Decimal(detail["amount_total"]) == Decimal("2000.00")

    # Adjustments are listed and unapplied.
    adj = admin_client.get(f"/api/subscriptions/{sid}/adjustments").json()
    assert adj["total"] == 2
    assert all(a["applied"] is False for a in adj["items"])


def test_change_rejected_when_not_active(admin_client: TestClient) -> None:
    # A brand-new DRAFT subscription cannot take a proration change.
    product = admin_client.post(
        "/api/products",
        json={"name": "P", "type": "SOFTWARE", "sales_price": "100.00", "cost_price": "10.00"},
    ).json()
    today = date.today()
    plan = admin_client.post(
        "/api/plans",
        json={
            "name": "M",
            "price": "100.00",
            "billing_period": "MONTHLY",
            "available_from": today.isoformat(),
            "available_to": (today + timedelta(days=365)).isoformat(),
        },
    ).json()
    customer = admin_client.post("/api/customers", json={"name": "C", "email": "c@example.com"}).json()
    sub = admin_client.post(
        "/api/subscriptions",
        json={
            "customer_id": customer["id"],
            "plan_id": plan["id"],
            "start_date": today.isoformat(),
            "expiry_date": (today + timedelta(days=30)).isoformat(),
            "lines": [{"product_id": product["id"], "quantity": 1}],
        },
    ).json()
    resp = admin_client.post(
        f"/api/subscriptions/{sub['id']}/change",
        json={"lines": [{"product_id": product["id"], "quantity": 2}]},
    )
    assert resp.status_code == 409, resp.text

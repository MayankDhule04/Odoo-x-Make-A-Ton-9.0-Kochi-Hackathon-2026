"""Quotation templates and create-from-template."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient


def test_create_subscription_from_template(admin_client: TestClient) -> None:
    product = admin_client.post(
        "/api/products",
        json={"name": "Pro", "type": "SOFTWARE", "sales_price": "1000.00", "cost_price": "100.00"},
    ).json()
    today = date.today()
    plan = admin_client.post(
        "/api/plans",
        json={
            "name": "Monthly",
            "price": "999.00",
            "billing_period": "MONTHLY",
            "available_from": today.isoformat(),
            "available_to": (today + timedelta(days=365)).isoformat(),
        },
    ).json()
    customer = admin_client.post("/api/customers", json={"name": "Acme", "email": "a@example.com"}).json()

    template = admin_client.post(
        "/api/quotation-templates",
        json={
            "name": "Standard Pro",
            "plan_id": plan["id"],
            "validity_days": 14,
            "lines": [{"product_id": product["id"], "quantity": 3}],
        },
    )
    assert template.status_code == 201, template.text
    tid = template.json()["id"]

    resp = admin_client.post(
        "/api/subscriptions/from-template",
        json={"template_id": tid, "customer_id": customer["id"], "start_date": today.isoformat()},
    )
    assert resp.status_code == 201, resp.text
    sub = resp.json()

    # Lines copied; unit price derived from the product's effective price.
    assert len(sub["lines"]) == 1
    assert sub["lines"][0]["quantity"] == 3
    assert Decimal(sub["lines"][0]["unit_price"]) == Decimal("1000.00")
    assert Decimal(sub["amount_total"]) == Decimal("3000.00")
    # Expiry defaults to start + validity_days.
    assert sub["expiry_date"] == (today + timedelta(days=14)).isoformat()


def test_template_crud(admin_client: TestClient) -> None:
    plan = admin_client.post(
        "/api/plans",
        json={
            "name": "P",
            "price": "1.00",
            "billing_period": "MONTHLY",
            "available_from": date.today().isoformat(),
            "available_to": (date.today() + timedelta(days=10)).isoformat(),
        },
    ).json()
    created = admin_client.post(
        "/api/quotation-templates", json={"name": "T", "plan_id": plan["id"], "validity_days": 30}
    ).json()
    tid = created["id"]
    upd = admin_client.patch(f"/api/quotation-templates/{tid}", json={"validity_days": 7})
    assert upd.status_code == 200
    assert upd.json()["validity_days"] == 7
    assert admin_client.delete(f"/api/quotation-templates/{tid}").status_code == 204
    assert admin_client.get(f"/api/quotation-templates/{tid}").status_code == 404

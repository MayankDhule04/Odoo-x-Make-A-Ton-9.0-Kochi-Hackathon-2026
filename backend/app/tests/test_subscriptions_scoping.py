"""RBAC and customer scoping for subscriptions."""

from datetime import date, timedelta

from fastapi.testclient import TestClient


def _plan_and_product(admin_client: TestClient) -> tuple[dict, dict]:
    product = admin_client.post(
        "/api/products",
        json={"name": "P", "type": "SOFTWARE", "sales_price": "100.00", "cost_price": "10.00"},
    ).json()
    today = date.today()
    plan = admin_client.post(
        "/api/plans",
        json={
            "name": "Plan",
            "price": "100.00",
            "billing_period": "MONTHLY",
            "available_from": today.isoformat(),
            "available_to": (today + timedelta(days=365)).isoformat(),
        },
    ).json()
    return product, plan


def _make_sub(admin_client: TestClient, product: dict, plan: dict, customer_id: int) -> dict:
    today = date.today()
    return admin_client.post(
        "/api/subscriptions",
        json={
            "customer_id": customer_id,
            "plan_id": plan["id"],
            "start_date": today.isoformat(),
            "expiry_date": (today + timedelta(days=30)).isoformat(),
            "lines": [{"product_id": product["id"], "quantity": 1}],
        },
    ).json()


def test_customer_cannot_create_subscription(customer_client: TestClient, admin_client: TestClient) -> None:
    product, plan = _plan_and_product(admin_client)
    me = customer_client.get("/api/customers/me").json()
    resp = customer_client.post(
        "/api/subscriptions",
        json={
            "customer_id": me["id"],
            "plan_id": plan["id"],
            "start_date": date.today().isoformat(),
            "expiry_date": (date.today() + timedelta(days=30)).isoformat(),
            "lines": [],
        },
    )
    assert resp.status_code == 403


def test_customer_sees_only_their_own(customer_client: TestClient, admin_client: TestClient) -> None:
    product, plan = _plan_and_product(admin_client)
    me = customer_client.get("/api/customers/me").json()
    other = admin_client.post("/api/customers", json={"name": "Other", "email": "other@example.com"}).json()

    mine = _make_sub(admin_client, product, plan, me["id"])
    theirs = _make_sub(admin_client, product, plan, other["id"])

    listed = customer_client.get("/api/subscriptions").json()
    ids = {s["id"] for s in listed["items"]}
    assert mine["id"] in ids
    assert theirs["id"] not in ids

    assert customer_client.get(f"/api/subscriptions/{mine['id']}").status_code == 200
    assert customer_client.get(f"/api/subscriptions/{theirs['id']}").status_code == 404


def test_staff_sees_all(staff_client: TestClient, admin_client: TestClient) -> None:
    product, plan = _plan_and_product(admin_client)
    customer = admin_client.post("/api/customers", json={"name": "C", "email": "c@example.com"}).json()
    sub = _make_sub(admin_client, product, plan, customer["id"])
    assert staff_client.get(f"/api/subscriptions/{sub['id']}").status_code == 200

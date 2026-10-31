"""Subscription lifecycle: numbering, state machine, illegal transitions, pause/renew."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient


def _setup(client: TestClient, **plan_flags) -> tuple[dict, dict, dict]:
    product = client.post(
        "/api/products",
        json={"name": "Brightloop Pro", "type": "SOFTWARE", "sales_price": "1000.00", "cost_price": "400.00"},
    ).json()
    today = date.today()
    plan = client.post(
        "/api/plans",
        json={
            "name": "Monthly",
            "price": "999.00",
            "billing_period": "MONTHLY",
            "available_from": (today - timedelta(days=5)).isoformat(),
            "available_to": (today + timedelta(days=365)).isoformat(),
            **plan_flags,
        },
    ).json()
    customer = client.post("/api/customers", json={"name": "Acme", "email": "acme@example.com"}).json()
    return product, plan, customer


def _create_sub(client: TestClient, product: dict, plan: dict, customer: dict, qty: int = 2) -> dict:
    today = date.today()
    resp = client.post(
        "/api/subscriptions",
        json={
            "customer_id": customer["id"],
            "plan_id": plan["id"],
            "start_date": today.isoformat(),
            "expiry_date": (today + timedelta(days=30)).isoformat(),
            "lines": [{"product_id": product["id"], "quantity": qty}],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_numbering_and_line_amounts(admin_client: TestClient) -> None:
    product, plan, customer = _setup(admin_client)
    sub = _create_sub(admin_client, product, plan, customer, qty=2)

    assert sub["status"] == "DRAFT"
    assert sub["number"].startswith(f"SUB-{date.today().year}-")
    assert Decimal(sub["lines"][0]["unit_price"]) == Decimal("1000.00")
    assert Decimal(sub["lines"][0]["amount"]) == Decimal("2000.00")
    assert Decimal(sub["amount_total"]) == Decimal("2000.00")


def test_happy_path_transitions(admin_client: TestClient) -> None:
    product, plan, customer = _setup(admin_client)
    sub = _create_sub(admin_client, product, plan, customer)
    sid = sub["id"]

    assert admin_client.post(f"/api/subscriptions/{sid}/submit", json={}).json()["status"] == "QUOTATION"
    assert admin_client.post(f"/api/subscriptions/{sid}/confirm", json={}).json()["status"] == "CONFIRMED"
    activated = admin_client.post(f"/api/subscriptions/{sid}/activate", json={}).json()
    assert activated["status"] == "ACTIVE"
    # Billing clock starts at the start date.
    assert activated["next_billing_date"] == sub["start_date"]


def test_illegal_transition_is_rejected(admin_client: TestClient) -> None:
    product, plan, customer = _setup(admin_client)
    sub = _create_sub(admin_client, product, plan, customer)
    # DRAFT -> ACTIVE is not allowed.
    resp = admin_client.post(f"/api/subscriptions/{sub['id']}/activate", json={})
    assert resp.status_code == 409, resp.text


def test_pause_resume_requires_flag(admin_client: TestClient) -> None:
    product, plan, customer = _setup(admin_client, allow_pause=False)
    sub = _create_sub(admin_client, product, plan, customer)
    sid = sub["id"]
    admin_client.post(f"/api/subscriptions/{sid}/submit", json={})
    admin_client.post(f"/api/subscriptions/{sid}/confirm", json={})
    admin_client.post(f"/api/subscriptions/{sid}/activate", json={})

    # Plan forbids pausing.
    assert admin_client.post(f"/api/subscriptions/{sid}/pause", json={}).status_code == 409


def test_pause_resume_close_renew(admin_client: TestClient) -> None:
    product, plan, customer = _setup(admin_client)  # all flags default True
    sub = _create_sub(admin_client, product, plan, customer)
    sid = sub["id"]
    original_expiry = sub["expiry_date"]
    admin_client.post(f"/api/subscriptions/{sid}/submit", json={})
    admin_client.post(f"/api/subscriptions/{sid}/confirm", json={})
    admin_client.post(f"/api/subscriptions/{sid}/activate", json={})

    assert admin_client.post(f"/api/subscriptions/{sid}/pause", json={}).json()["status"] == "PAUSED"
    assert admin_client.post(f"/api/subscriptions/{sid}/resume", json={}).json()["status"] == "ACTIVE"
    assert admin_client.post(f"/api/subscriptions/{sid}/close", json={}).json()["status"] == "CLOSED"

    renewed = admin_client.post(f"/api/subscriptions/{sid}/renew", json={}).json()
    assert renewed["status"] == "ACTIVE"
    assert renewed["expiry_date"] > original_expiry  # extended by one month


def test_history_timeline_records_every_change(admin_client: TestClient) -> None:
    product, plan, customer = _setup(admin_client)
    sub = _create_sub(admin_client, product, plan, customer)
    sid = sub["id"]
    admin_client.post(f"/api/subscriptions/{sid}/submit", json={})
    admin_client.post(f"/api/subscriptions/{sid}/confirm", json={})

    history = admin_client.get(f"/api/subscriptions/{sid}/history").json()["items"]
    # created (-> DRAFT), -> QUOTATION, -> CONFIRMED
    assert [h["to_status"] for h in history] == ["DRAFT", "QUOTATION", "CONFIRMED"]
    assert history[0]["from_status"] is None
    assert history[1]["from_status"] == "DRAFT"
    assert history[2]["from_status"] == "QUOTATION"


def test_edit_only_while_draft_or_quotation(admin_client: TestClient) -> None:
    product, plan, customer = _setup(admin_client)
    sub = _create_sub(admin_client, product, plan, customer)
    sid = sub["id"]

    # Editing a draft is fine.
    ok = admin_client.patch(f"/api/subscriptions/{sid}", json={"payment_terms": "NET_30"})
    assert ok.status_code == 200
    assert ok.json()["payment_terms"] == "NET_30"

    # Once active, edits are rejected.
    admin_client.post(f"/api/subscriptions/{sid}/submit", json={})
    admin_client.post(f"/api/subscriptions/{sid}/confirm", json={})
    admin_client.post(f"/api/subscriptions/{sid}/activate", json={})
    assert admin_client.patch(f"/api/subscriptions/{sid}", json={"payment_terms": "IMMEDIATE"}).status_code == 409

"""Dunning (#1) and revenue-at-risk (#5)."""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.tests.billing_setup import overdue_invoice


def test_dunning_sends_reminders_and_suspends(admin_client: TestClient) -> None:
    _invoice, sid, _cid = overdue_invoice(admin_client, days_overdue=20)

    run = admin_client.post("/api/payments/dunning/run", json={})
    assert run.status_code == 200, run.text
    body = run.json()
    # 20 days overdue: reminders at day 1,3,5,7 (four), then suspension.
    assert body["reminders_sent"] == 4
    assert body["suspensions"] == 1

    sub = admin_client.get(f"/api/subscriptions/{sid}").json()
    assert sub["status"] == "PAUSED"


def test_dunning_is_idempotent(admin_client: TestClient) -> None:
    overdue_invoice(admin_client, days_overdue=20)
    admin_client.post("/api/payments/dunning/run", json={})
    second = admin_client.post("/api/payments/dunning/run", json={}).json()
    assert second["reminders_sent"] == 0
    assert second["suspensions"] == 0


def test_revenue_at_risk_lists_and_reminds(admin_client: TestClient) -> None:
    invoice, sid, _cid = overdue_invoice(admin_client, days_overdue=20)

    rar = admin_client.get("/api/payments/revenue-at-risk").json()
    assert Decimal(rar["total_at_risk"]) >= Decimal(invoice["amount_total"])
    item = next(i for i in rar["items"] if i["subscription_id"] == sid)
    assert item["days_overdue"] >= 20
    assert item["invoice_count"] >= 1

    remind = admin_client.post(f"/api/payments/revenue-at-risk/{sid}/remind")
    assert remind.status_code == 200, remind.text
    assert "Sent 1" in remind.json()["message"]


def test_status_summary_counts_overdue(admin_client: TestClient) -> None:
    invoice, _sid, _cid = overdue_invoice(admin_client, days_overdue=20)
    summary = admin_client.get("/api/payments/summary").json()
    assert summary["overdue"] >= 1
    assert Decimal(summary["total_overdue"]) >= Decimal(invoice["amount_total"])


def test_dunning_run_is_staff_only(customer_client: TestClient) -> None:
    assert customer_client.post("/api/payments/dunning/run", json={}).status_code == 403

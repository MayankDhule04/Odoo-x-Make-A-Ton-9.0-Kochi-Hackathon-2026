"""Finance dashboard, MRR analytics and CSV export."""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.tests.billing_setup import billed_invoice


def test_dashboard_summary(admin_client: TestClient) -> None:
    invoice, _sid, _cid = billed_invoice(admin_client)
    total = Decimal(invoice["amount_total"])
    admin_client.post("/api/payments", json={"invoice_id": invoice["id"], "amount": "400.00", "method": "UPI"})

    summary = admin_client.get("/api/reporting/dashboard").json()
    assert summary["active_subscriptions"] >= 1
    assert Decimal(summary["revenue_collected"]) >= Decimal("400.00")
    assert Decimal(summary["amount_owed"]) >= total - Decimal("400.00")


def test_mrr_analytics_has_waterfall(admin_client: TestClient) -> None:
    billed_invoice(admin_client)
    mrr = admin_client.get("/api/reporting/mrr").json()
    assert Decimal(mrr["mrr"]) > 0
    assert mrr["active_subscriptions"] >= 1
    assert len(mrr["waterfall"]) == 6
    # The subscription activated this month, so the latest month shows New MRR.
    assert Decimal(mrr["waterfall"][-1]["new"]) > 0


def test_invoices_csv_export(admin_client: TestClient) -> None:
    invoice, _sid, _cid = billed_invoice(admin_client)
    resp = admin_client.get("/api/reporting/invoices.csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "number,status,issue_date" in resp.text
    assert invoice["number"] in resp.text


def test_dashboard_is_staff_only(customer_client: TestClient) -> None:
    assert customer_client.get("/api/reporting/dashboard").status_code == 403

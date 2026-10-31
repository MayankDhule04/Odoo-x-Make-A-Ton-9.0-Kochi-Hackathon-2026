"""Payments (Phase 5a): partial/full payment, status derivation, overpayment, scoping."""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.tests.billing_setup import billed_invoice


def test_partial_then_full_payment_marks_paid(admin_client: TestClient) -> None:
    invoice, _sid, _cid = billed_invoice(admin_client)
    iid = invoice["id"]
    total = Decimal(invoice["amount_total"])
    half = (total / 2).quantize(Decimal("0.01"))

    p1 = admin_client.post("/api/payments", json={"invoice_id": iid, "amount": str(half), "method": "UPI"})
    assert p1.status_code == 201, p1.text
    after = admin_client.get(f"/api/invoices/{iid}").json()
    assert after["status"] == "CONFIRMED"
    assert Decimal(after["amount_paid"]) == half
    assert Decimal(after["amount_due"]) == total - half

    p2 = admin_client.post(
        "/api/payments", json={"invoice_id": iid, "amount": str(total - half), "method": "CASH"}
    )
    assert p2.status_code == 201, p2.text
    paid = admin_client.get(f"/api/invoices/{iid}").json()
    assert paid["status"] == "PAID"
    assert Decimal(paid["amount_due"]) == Decimal("0.00")


def test_overpayment_is_rejected(admin_client: TestClient) -> None:
    invoice, _sid, _cid = billed_invoice(admin_client)
    total = Decimal(invoice["amount_total"])
    resp = admin_client.post(
        "/api/payments", json={"invoice_id": invoice["id"], "amount": str(total + 1), "method": "CARD"}
    )
    assert resp.status_code == 409, resp.text


def test_cannot_pay_a_draft_invoice(admin_client: TestClient) -> None:
    customer = admin_client.post("/api/customers", json={"name": "Draft Co", "email": "d@example.com"}).json()
    invoice = admin_client.post(
        "/api/invoices",
        json={
            "customer_id": customer["id"],
            "due_date": "2027-01-01",
            "lines": [{"description": "Setup", "quantity": 1, "unit_price": "100.00", "amount": "100.00"}],
        },
    )
    assert invoice.status_code == 201, invoice.text
    iid = invoice.json()["id"]
    resp = admin_client.post("/api/payments", json={"invoice_id": iid, "amount": "100.00", "method": "CASH"})
    assert resp.status_code == 409  # must confirm first


def test_customer_sees_only_their_payments(customer_client: TestClient, admin_client: TestClient) -> None:
    me = customer_client.get("/api/customers/me").json()
    mine, _sid, _cid = billed_invoice(admin_client, customer_id=me["id"])
    admin_client.post("/api/payments", json={"invoice_id": mine["id"], "amount": "100.00", "method": "UPI"})

    other, _sid2, _cid2 = billed_invoice(admin_client)
    admin_client.post("/api/payments", json={"invoice_id": other["id"], "amount": "100.00", "method": "CASH"})

    listed = customer_client.get("/api/payments").json()
    assert listed["total"] == 1
    assert listed["items"][0]["customer_id"] == me["id"]

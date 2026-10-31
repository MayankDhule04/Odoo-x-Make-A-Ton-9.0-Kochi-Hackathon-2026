"""RBAC on catalog: writes are admin-only; discounts are admin-only even to read."""

from fastapi.testclient import TestClient

_PRODUCT = {"name": "X", "type": "SOFTWARE", "sales_price": "100.00", "cost_price": "10.00"}
_DISCOUNT = {
    "name": "Launch 10%",
    "type": "PERCENTAGE",
    "value": "10.00",
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
}


def test_admin_can_create_product(admin_client: TestClient) -> None:
    assert admin_client.post("/api/products", json=_PRODUCT).status_code == 201


def test_staff_cannot_create_product(staff_client: TestClient) -> None:
    assert staff_client.post("/api/products", json=_PRODUCT).status_code == 403


def test_customer_cannot_create_product(customer_client: TestClient) -> None:
    assert customer_client.post("/api/products", json=_PRODUCT).status_code == 403


def test_unauthenticated_cannot_create_product(client: TestClient) -> None:
    assert client.post("/api/products", json=_PRODUCT).status_code == 401


def test_staff_can_read_products(staff_client: TestClient) -> None:
    assert staff_client.get("/api/products").status_code == 200


def test_only_admin_can_create_discount(staff_client: TestClient, admin_client: TestClient) -> None:
    assert staff_client.post("/api/discounts", json=_DISCOUNT).status_code == 403
    assert admin_client.post("/api/discounts", json=_DISCOUNT).status_code == 201


def test_staff_cannot_read_discounts(staff_client: TestClient) -> None:
    assert staff_client.get("/api/discounts").status_code == 403

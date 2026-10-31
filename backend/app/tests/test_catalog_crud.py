"""Full CRUD for catalog: update/delete of products, variants, plans, taxes, discounts."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient


def _create_product(client: TestClient) -> dict:
    resp = client.post(
        "/api/products",
        json={
            "name": "Brightloop Pro",
            "type": "SOFTWARE",
            "sales_price": "1000.00",
            "cost_price": "400.00",
            "variants": [{"value": "Generic", "price_extra": "0.00"}],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_update_product_price(admin_client: TestClient) -> None:
    product = _create_product(admin_client)
    resp = admin_client.patch(f"/api/products/{product['id']}", json={"sales_price": "1200.00"})
    assert resp.status_code == 200, resp.text
    assert Decimal(resp.json()["sales_price"]) == Decimal("1200.00")
    assert Decimal(resp.json()["margin"]) == Decimal("800.00")


def test_delete_product(admin_client: TestClient) -> None:
    product = _create_product(admin_client)
    assert admin_client.delete(f"/api/products/{product['id']}").status_code == 204
    assert admin_client.get(f"/api/products/{product['id']}").status_code == 404


def test_variant_add_update_delete(admin_client: TestClient) -> None:
    product = _create_product(admin_client)
    pid = product["id"]

    # Add the Odoo +560 variant; effective price reflects base + extra.
    add = admin_client.post(
        f"/api/products/{pid}/variants", json={"value": "Odoo", "price_extra": "560.00"}
    )
    assert add.status_code == 201, add.text
    variant = add.json()
    assert Decimal(variant["effective_price"]) == Decimal("1560.00")

    # Update the extra.
    upd = admin_client.patch(
        f"/api/products/{pid}/variants/{variant['id']}", json={"price_extra": "600.00"}
    )
    assert upd.status_code == 200, upd.text
    assert Decimal(upd.json()["effective_price"]) == Decimal("1600.00")

    # Delete it.
    assert admin_client.delete(f"/api/products/{pid}/variants/{variant['id']}").status_code == 204
    remaining = admin_client.get(f"/api/products/{pid}").json()["variants"]
    assert all(v["value"] != "Odoo" for v in remaining)


def test_attribute_add_delete(admin_client: TestClient) -> None:
    product = _create_product(admin_client)
    pid = product["id"]
    add = admin_client.post(f"/api/products/{pid}/attributes", json={"name": "Brand"})
    assert add.status_code == 201, add.text
    attr_id = add.json()["id"]
    assert admin_client.delete(f"/api/products/{pid}/attributes/{attr_id}").status_code == 204


def _create_plan(client: TestClient) -> dict:
    today = date.today()
    resp = client.post(
        "/api/plans",
        json={
            "name": "Monthly",
            "price": "999.00",
            "billing_period": "MONTHLY",
            "available_from": (today - timedelta(days=1)).isoformat(),
            "available_to": (today + timedelta(days=30)).isoformat(),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_update_and_delete_plan(admin_client: TestClient) -> None:
    plan = _create_plan(admin_client)
    upd = admin_client.patch(f"/api/plans/{plan['id']}", json={"price": "1299.00", "allow_pause": False})
    assert upd.status_code == 200, upd.text
    assert Decimal(upd.json()["price"]) == Decimal("1299.00")
    assert upd.json()["allow_pause"] is False
    assert admin_client.delete(f"/api/plans/{plan['id']}").status_code == 204
    assert admin_client.get(f"/api/plans/{plan['id']}").status_code == 404


def test_update_and_delete_tax(admin_client: TestClient) -> None:
    created = admin_client.post("/api/taxes", json={"name": "GST", "percentage": "18.000"}).json()
    upd = admin_client.patch(f"/api/taxes/{created['id']}", json={"percentage": "12.000"})
    assert upd.status_code == 200, upd.text
    assert Decimal(upd.json()["percentage"]) == Decimal("12.000")
    assert admin_client.delete(f"/api/taxes/{created['id']}").status_code == 204


def test_update_and_delete_discount(admin_client: TestClient) -> None:
    created = admin_client.post(
        "/api/discounts",
        json={
            "name": "Launch 10%",
            "type": "PERCENTAGE",
            "value": "10.00",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
    ).json()
    upd = admin_client.patch(f"/api/discounts/{created['id']}", json={"value": "15.00"})
    assert upd.status_code == 200, upd.text
    assert Decimal(upd.json()["value"]) == Decimal("15.00")
    assert admin_client.delete(f"/api/discounts/{created['id']}").status_code == 204


def test_staff_cannot_update_or_delete(staff_client: TestClient, admin_client: TestClient) -> None:
    plan = _create_plan(admin_client)
    assert staff_client.patch(f"/api/plans/{plan['id']}", json={"price": "1.00"}).status_code == 403
    assert staff_client.delete(f"/api/plans/{plan['id']}").status_code == 403

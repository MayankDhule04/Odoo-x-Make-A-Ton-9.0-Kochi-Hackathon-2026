"""Catalog pricing: variant effective price (Odoo brand +560) and product margin."""

from decimal import Decimal

from fastapi.testclient import TestClient


def test_effective_price_adds_odoo_brand_extra(admin_client: TestClient) -> None:
    payload = {
        "name": "Brightloop Pro",
        "type": "SOFTWARE",
        "sales_price": "1000.00",
        "cost_price": "400.00",
        "notes": "flagship",
        "attributes": [{"name": "Brand"}],
        "variants": [
            {"value": "Generic", "price_extra": "0.00"},
            {"value": "Odoo", "price_extra": "560.00"},
        ],
    }
    resp = admin_client.post("/api/products", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()

    # Margin = sales - cost, serialized as a string.
    assert Decimal(body["margin"]) == Decimal("600.00")

    variants = {v["value"]: v for v in body["variants"]}
    assert Decimal(variants["Generic"]["effective_price"]) == Decimal("1000.00")
    assert Decimal(variants["Odoo"]["effective_price"]) == Decimal("1560.00")


def test_product_appears_in_list(admin_client: TestClient) -> None:
    admin_client.post(
        "/api/products",
        json={"name": "Widget", "type": "PHYSICAL", "sales_price": "50.00", "cost_price": "20.00"},
    )
    resp = admin_client.get("/api/products")
    assert resp.status_code == 200, resp.text
    page = resp.json()
    assert page["total"] >= 1
    assert any(p["name"] == "Widget" for p in page["items"])

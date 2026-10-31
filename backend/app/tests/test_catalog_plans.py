"""Plan availability: a plan outside its window cannot be selected for a new subscription."""

from datetime import date, timedelta

from fastapi.testclient import TestClient


def _make_plan(client: TestClient, name: str, start: date, end: date) -> dict:
    resp = client.post(
        "/api/plans",
        json={
            "name": name,
            "price": "999.00",
            "billing_period": "MONTHLY",
            "min_quantity": 1,
            "available_from": start.isoformat(),
            "available_to": end.isoformat(),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_plan_outside_window_is_not_selectable(admin_client: TestClient) -> None:
    today = date.today()
    current = _make_plan(admin_client, "Current", today - timedelta(days=5), today + timedelta(days=30))
    expired = _make_plan(admin_client, "Expired", today - timedelta(days=60), today - timedelta(days=30))
    future = _make_plan(admin_client, "Future", today + timedelta(days=30), today + timedelta(days=90))

    resp = admin_client.get("/api/plans/selectable")
    assert resp.status_code == 200, resp.text
    selectable_ids = {p["id"] for p in resp.json()}

    assert current["id"] in selectable_ids
    assert expired["id"] not in selectable_ids
    assert future["id"] not in selectable_ids


def test_selectable_respects_explicit_date(admin_client: TestClient) -> None:
    today = date.today()
    future = _make_plan(admin_client, "Future", today + timedelta(days=30), today + timedelta(days=90))

    on = (today + timedelta(days=45)).isoformat()
    resp = admin_client.get("/api/plans/selectable", params={"on": on})
    assert resp.status_code == 200, resp.text
    assert future["id"] in {p["id"] for p in resp.json()}


def test_plan_rejects_inverted_window(admin_client: TestClient) -> None:
    today = date.today()
    resp = admin_client.post(
        "/api/plans",
        json={
            "name": "Bad",
            "price": "10.00",
            "billing_period": "MONTHLY",
            "available_from": today.isoformat(),
            "available_to": (today - timedelta(days=1)).isoformat(),
        },
    )
    assert resp.status_code == 422, resp.text

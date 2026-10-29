from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_plans_reads_seeded_rows() -> None:
    response = client.get("/api/v1/plans")
    assert response.status_code == 200
    body = response.json()
    ids = {plan["id"] for plan in body["plans"]}
    assert {"sandbox", "micro", "pro"} <= ids
    micro = next(plan for plan in body["plans"] if plan["id"] == "micro")
    assert micro["max_ponds"] == 1
    assert micro["price_monthly_usd"] == 5.0
    assert micro["billing_model"] == "monthly"
    assert micro["unit_price"] == 5.0
    assert micro["currency"] == "USD"
    assert micro["active"] is True

    pro = next(plan for plan in body["plans"] if plan["id"] == "pro")
    assert pro["billing_model"] == "hourly"
    assert pro["unit_price"] == 0.02
    assert pro["currency"] == "USD"
    assert pro["price_monthly_usd"] == 0.0

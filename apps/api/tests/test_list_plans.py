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
    assert micro["active"] is True
    assert micro["backup_retention_days"] == 7
    pro = next(plan for plan in body["plans"] if plan["id"] == "pro")
    assert pro["backup_retention_days"] == 30
    sandbox = next(plan for plan in body["plans"] if plan["id"] == "sandbox")
    assert sandbox["backup_retention_days"] == 0

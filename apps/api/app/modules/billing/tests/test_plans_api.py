from __future__ import annotations

from typing import Any

from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.main import app
from app.modules.billing import BillingService
from app.modules.billing.payments import get_payment_provider
from app.schemas import PlanListResponse, PlanOut

SEEDED_PLANS: dict[str, dict[str, Any]] = {
    "sandbox": {
        "id": "sandbox",
        "name": "Sandbox",
        "description": "Pruebas internas (10 min)",
        "price_monthly_usd": 0.0,
        "max_ponds": 1,
        "max_storage_gb": 1,
        "validity_minutes": 10,
        "postpaid": False,
        "active": True,
    },
    "micro": {
        "id": "micro",
        "name": "Micro",
        "description": "1 pond, 1 GB, backups 7 días",
        "price_monthly_usd": 5.0,
        "max_ponds": 1,
        "max_storage_gb": 1,
        "validity_minutes": 43200,
        "postpaid": False,
        "active": True,
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "description": "Hasta 10 ponds, post-pago por uso",
        "price_monthly_usd": 0.0,
        "max_ponds": 10,
        "max_storage_gb": 20,
        "validity_minutes": 43200,
        "postpaid": True,
        "active": True,
    },
}


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_list_plans_public_happy_path() -> None:
    async with _make_client() as client:
        response = await client.get("/api/v1/plans")

    assert response.status_code == 200
    body = response.json()
    assert "plans" in body
    plans = body["plans"]
    assert len(plans) == 3

    plan_ids = [p["id"] for p in plans]
    assert plan_ids == sorted(plan_ids)
    assert plan_ids == ["micro", "pro", "sandbox"]

    for plan in plans:
        expected = SEEDED_PLANS[plan["id"]]
        for field, expected_val in expected.items():
            assert plan[field] == expected_val, (
                f"Mismatch in {plan['id']}.{field}: {plan[field]} != {expected_val}"
            )


async def test_billing_service_list_plans() -> None:
    settings = get_settings()
    async with SessionLocal() as session:
        service = BillingService(session, settings, get_payment_provider(settings))
        result = await service.list_plans()

    assert isinstance(result, PlanListResponse)
    assert len(result.plans) == 3
    assert [p.id for p in result.plans] == ["micro", "pro", "sandbox"]

    for plan in result.plans:
        assert isinstance(plan, PlanOut)
        expected = SEEDED_PLANS[plan.id]
        assert plan.name == expected["name"]
        assert plan.description == expected["description"]
        assert plan.price_monthly_usd == expected["price_monthly_usd"]
        assert plan.max_ponds == expected["max_ponds"]
        assert plan.max_storage_gb == expected["max_storage_gb"]
        assert plan.validity_minutes == expected["validity_minutes"]
        assert plan.postpaid == expected["postpaid"]
        assert plan.active == expected["active"]


def test_plan_schemas_have_openapi_examples() -> None:
    openapi_spec = app.openapi()
    schemas = openapi_spec.get("components", {}).get("schemas", {})

    assert "PlanOut" in schemas
    plan_out_schema = schemas["PlanOut"]
    assert "example" in plan_out_schema
    example = plan_out_schema["example"]
    assert example["id"] == "micro"
    assert example["name"] == "Micro"
    assert example["price_monthly_usd"] == 5.0
    assert example["active"] is True

    assert "PlanListResponse" in schemas
    plan_list_schema = schemas["PlanListResponse"]
    assert "example" in plan_list_schema
    list_example = plan_list_schema["example"]
    assert "plans" in list_example
    assert len(list_example["plans"]) >= 1

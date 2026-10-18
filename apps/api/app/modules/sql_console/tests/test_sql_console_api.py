from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select, text

from app.core.config import get_settings, to_sync_database_url
from app.core.db import SessionLocal
from app.core.enums import EmailTokenKind, SQLMode
from app.core.errors import AppError, app_error_handler
from app.core.time import utc_now
from app.main import app as main_app
from app.modules.auth import AuthService
from app.modules.sql_console.models import SqlHistory
from app.modules.sql_console.router import router as sql_router
from app.modules.sql_console.service import QUERY_MAX_CHARS, HistoryWrite, SqlConsoleService
from app.schemas import SQLResultResponse
from tests.db_reset import DEMO_EMAIL, DEMO_PASSWORD, ensure_demo_user, reset_pond_tables


def _console_app() -> FastAPI:
    application = FastAPI()
    application.add_exception_handler(AppError, app_error_handler)
    application.include_router(sql_router, prefix="/api/v1")
    return application


def _reset() -> None:
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM sql_history"))
    engine.dispose()
    reset_pond_tables()


def _client(application: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=application), base_url="http://test")


async def _login(client: AsyncClient, email: str = DEMO_EMAIL) -> tuple[str, UUID]:
    if email == DEMO_EMAIL:
        ensure_demo_user()
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    return body["access_token"], UUID(body["user"]["id"])


async def _pond(client: AsyncClient, token: str, name: str) -> UUID:
    created = await client.post(
        "/api/v1/ponds",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name},
    )
    assert created.status_code == 202, created.text
    return UUID(created.json()["pond"]["id"])


async def _record(user_id: UUID, pond_id: UUID, query: str) -> None:
    async with SessionLocal() as session:
        await SqlConsoleService(session).record(
            HistoryWrite(
                user_id=user_id,
                pond_id=pond_id,
                query=query,
                mode=SQLMode.READ,
                row_count=1,
                duration_ms=4,
            )
        )
        await session.commit()


async def test_run_sql_delegates_once_and_does_not_parse(monkeypatch) -> None:
    _reset()
    seen: list[tuple[str, str | None]] = []

    async def fake_run_sql(pond_id, payload, *, actor, surface, confirm_token=None):
        seen.append((payload.query, confirm_token))
        return SQLResultResponse(
            columns=["?column?"],
            rows=[[1]],
            row_count=1,
            duration_ms=4,
            truncated=False,
        )

    monkeypatch.setattr("app.modules.sql_console.router.sql_commands.run_sql", fake_run_sql)

    async with _client(main_app) as api, _client(_console_app()) as client:
        token, _user_id = await _login(api)
        pond_id = await _pond(api, token, "sql-delegate")
        query = "SELECT 1; DROP TABLE ponds"
        response = await client.post(
            f"/api/v1/ponds/{pond_id}/sql",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": query, "mode": "read"},
        )

    assert response.status_code == 200
    assert response.json()["columns"] == ["?column?"]
    assert seen == [(query, None)]


async def test_run_sql_rejects_a_body_without_query() -> None:
    _reset()
    async with _client(main_app) as api, _client(_console_app()) as client:
        token, _user_id = await _login(api)
        response = await client.post(
            f"/api/v1/ponds/{UUID(int=1)}/sql",
            headers={"Authorization": f"Bearer {token}"},
            json={"mode": "read"},
        )
    assert response.status_code == 422


def _extra_pond(owner_id: UUID, name: str) -> UUID:
    """Bypass plan quota so actor+pond scoping can use a second pond."""
    from uuid import uuid4

    pond_id = uuid4()
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    with engine.begin() as connection:
        node_id = connection.execute(text("SELECT id FROM nodes LIMIT 1")).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO ponds (
                    id, user_id, plan_id, node_id, name, engine_version,
                    desired_state, host_port, db_password_encrypted
                )
                VALUES (
                    :id, :user_id, 'micro', :node_id, :name, '16',
                    'running', 15999, 'encrypted'
                )
                """
            ),
            {"id": str(pond_id), "user_id": str(owner_id), "node_id": node_id, "name": name},
        )
    engine.dispose()
    return pond_id


async def test_history_is_truncated_paginated_and_scoped() -> None:
    _reset()
    async with _client(main_app) as api, _client(_console_app()) as client:
        token, owner_id = await _login(api)
        pond_id = await _pond(api, token, "sql-history")
        other_pond = _extra_pond(owner_id, "sql-other")

        await _record(owner_id, pond_id, "Q" * (QUERY_MAX_CHARS + 500))
        await _record(owner_id, pond_id, "SELECT 2")
        await _record(owner_id, pond_id, "SELECT 3")
        await _record(owner_id, other_pond, "SELECT secret")

        async with SessionLocal() as session:
            rows = list(
                (
                    await session.execute(
                        select(SqlHistory).where(SqlHistory.pond_id == pond_id)
                    )
                ).scalars().all()
            )
            by_query = {row.query_truncated: row for row in rows}
            base = utc_now()
            by_query["Q" * QUERY_MAX_CHARS].executed_at = base + timedelta(seconds=1)
            by_query["SELECT 2"].executed_at = base + timedelta(seconds=2)
            by_query["SELECT 3"].executed_at = base + timedelta(seconds=3)
            await session.commit()

        headers = {"Authorization": f"Bearer {token}"}
        first = await client.get(
            f"/api/v1/ponds/{pond_id}/sql/history",
            headers=headers,
            params={"limit": 2},
        )
        assert first.status_code == 200
        body = first.json()
        assert [event["query_truncated"] for event in body["events"]] == ["SELECT 3", "SELECT 2"]
        assert body["next_cursor"]

        second = await client.get(
            f"/api/v1/ponds/{pond_id}/sql/history",
            headers=headers,
            params={"limit": 2, "cursor": body["next_cursor"]},
        )
        assert second.status_code == 200
        older = second.json()
        assert len(older["events"]) == 1
        assert older["events"][0]["query_truncated"] == "Q" * QUERY_MAX_CHARS
        assert older["next_cursor"] is None

        hidden = await client.get(
            f"/api/v1/ponds/{other_pond}/sql/history",
            headers=headers,
            params={"limit": 10},
        )
        assert [event["query_truncated"] for event in hidden.json()["events"]] == ["SELECT secret"]

        registered = await api.post(
            "/api/v1/auth/register",
            json={
                "email": "sql-other@koicloud.dev",
                "password": DEMO_PASSWORD,
                "full_name": "Otra persona",
            },
        )
        assert registered.status_code == 201
        stranger_id = UUID(registered.json()["user_id"])
        verify = await AuthService.issue_email_token(stranger_id, EmailTokenKind.VERIFY_EMAIL)
        assert (await api.post("/api/v1/auth/verify", json={"token": verify})).status_code == 200
        stranger, _stranger_id = await _login(api, "sql-other@koicloud.dev")
        foreign = await client.get(
            f"/api/v1/ponds/{pond_id}/sql/history",
            headers={"Authorization": f"Bearer {stranger}"},
        )
        assert foreign.status_code == 200
        assert foreign.json()["events"] == []

        bad = await client.get(
            f"/api/v1/ponds/{pond_id}/sql/history",
            headers=headers,
            params={"cursor": "not-a-cursor"},
        )
        assert bad.status_code == 422

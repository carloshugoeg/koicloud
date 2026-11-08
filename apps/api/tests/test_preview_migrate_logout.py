"""Preview startup must reach revision 0005 before a logged-in call.

The shared preview database is migrated by the Vercel entry, not by deploy.yml.
A database left at 0004 makes GET /me fail. Startup on preview upgrades it.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text

from alembic import command
from app.core.config import get_settings, to_sync_database_url
from app.main import app
from app.modules.auth.tests.test_auth_api import PASSWORD, _register_and_verify
from tests.db_reset import reset_auth_tables
from tests.test_preview_api_entry import _load_index

HEAD = "0007_temp_sql_confirm"
BEFORE = "0004_billing_payment_port"
API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = API_ROOT / "alembic" / "versions" / "0005_revoked_access_tokens.py"


def test_revision_0005_only_adds_revoked_access_tokens() -> None:
    """Shared preview DBs already have 0001-0004. This revision must only add a table."""
    upgrade = MIGRATION.read_text().split("def upgrade", 1)[1].split("def downgrade", 1)[0]
    assert 'op.create_table(\n        "revoked_access_tokens"' in upgrade
    for forbidden in ("op.drop_", "op.alter_", "op.rename_", "op.execute", "DELETE ", "UPDATE "):
        assert forbidden not in upgrade


def _config() -> Config:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "alembic"))
    return config


def _revision() -> str:
    engine = create_engine(to_sync_database_url(get_settings().database_url))
    try:
        with engine.connect() as connection:
            value = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    finally:
        engine.dispose()
    return str(value)


def _downgrade_to_0004() -> None:
    command.downgrade(_config(), BEFORE)


def _restore_head() -> None:
    if _revision() != HEAD:
        command.upgrade(_config(), HEAD)


async def _quiet_lifespan(_app: object) -> None:
    return None


def _start(monkeypatch: pytest.MonkeyPatch, vercel_env: str | None) -> None:
    monkeypatch.setenv("KOI_DB_SCHEMA", "koicloud")
    mod = _load_index(monkeypatch, vercel_env)
    monkeypatch.setattr(mod, "_lifespan_startup", _quiet_lifespan)
    mod._ensure_lifespan(mod._get_app())
    mod._lifespan_started = False
    mod._ensure_lifespan(mod._get_app())


def test_non_preview_startup_leaves_revision_0004(monkeypatch: pytest.MonkeyPatch) -> None:
    _downgrade_to_0004()
    try:
        _start(monkeypatch, "production")
        assert _revision() == BEFORE
    finally:
        _restore_head()


async def _logout_sequence() -> None:
    reset_auth_tables()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _register_and_verify(client, "preview-migrate@koicloud.dev")
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": "preview-migrate@koicloud.dev", "password": PASSWORD},
        )
        assert login_res.status_code == 200
        access = login_res.json()["access_token"]

        before = await client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert before.status_code == 200

        logout_res = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert logout_res.status_code == 204

        after = await client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert after.status_code == 401
        assert after.json()["code"] == "token_invalid"


def test_preview_startup_migrates_then_logout_rejects_old_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _downgrade_to_0004()
    try:
        assert _revision() == BEFORE
        _start(monkeypatch, "preview")
        assert _revision() == HEAD
        asyncio.run(_logout_sequence())
    finally:
        _restore_head()

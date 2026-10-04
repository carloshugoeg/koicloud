from __future__ import annotations

from uuid import uuid4

from sqlalchemy import create_engine, text

from app.core.config import get_settings, to_sync_database_url
from app.core.security import hash_password

DEMO_EMAIL = "demo@koicloud.dev"
DEMO_PASSWORD = "Sup3rSegura!2026"


def _engine():
    return create_engine(to_sync_database_url(get_settings().database_url))


def reset_pond_tables() -> None:
    engine = _engine()
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM pending_confirmations"))
        connection.execute(text("DELETE FROM jobs"))
        connection.execute(text("DELETE FROM backups"))
        connection.execute(text("DELETE FROM usage_daily"))
        connection.execute(text("DELETE FROM pond_samples"))
        connection.execute(text("DELETE FROM pond_status"))
        connection.execute(text("DELETE FROM ponds"))
        connection.execute(text("DELETE FROM subscriptions"))
        connection.execute(text("DELETE FROM refresh_tokens"))
        connection.execute(text("DELETE FROM email_tokens"))
        connection.execute(text("DELETE FROM agent_access"))
        connection.execute(text("DELETE FROM users"))
        connection.execute(text("DELETE FROM nodes"))
    engine.dispose()


def reset_auth_tables() -> None:
    engine = _engine()
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM pending_confirmations"))
        connection.execute(text("DELETE FROM refresh_tokens"))
        connection.execute(text("DELETE FROM email_tokens"))
        connection.execute(text("DELETE FROM jobs"))
        connection.execute(text("DELETE FROM backups"))
        connection.execute(text("DELETE FROM usage_daily"))
        connection.execute(text("DELETE FROM pond_samples"))
        connection.execute(text("DELETE FROM pond_status"))
        connection.execute(text("DELETE FROM ponds"))
        connection.execute(text("DELETE FROM subscriptions"))
        connection.execute(text("DELETE FROM agent_access"))
        connection.execute(text("DELETE FROM users"))
    engine.dispose()


def ensure_demo_user() -> None:
    settings = get_settings()
    engine = _engine()
    with engine.begin() as connection:
        existing = connection.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": DEMO_EMAIL},
        ).first()
        if existing is None:
            user_id = str(uuid4())
            connection.execute(
                text(
                    """
                    INSERT INTO users (
                        id, email, password_hash, full_name, role, status, email_verified_at
                    )
                    VALUES (
                        :id, :email, :password_hash, :full_name, 'client', 'active', CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "id": user_id,
                    "email": DEMO_EMAIL,
                    "password_hash": hash_password(DEMO_PASSWORD),
                    "full_name": "Demo Koi",
                },
            )
        else:
            user_id = str(existing[0])

        access = connection.execute(
            text("SELECT id FROM agent_access WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).first()
        if access is None:
            connection.execute(
                text(
                    """
                    INSERT INTO agent_access (
                        id, user_id, access_slug, password_hash, enabled, rotated_at
                    )
                    VALUES (
                        :id, :user_id, :slug, :password_hash, true, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "slug": settings.mcp_demo_slug,
                    "password_hash": hash_password(settings.mcp_demo_password),
                },
            )
    engine.dispose()

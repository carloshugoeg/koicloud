"""Preview-only admin seed for Vercel (never production).

Reads KOI_PREVIEW_ADMIN_EMAIL / KOI_PREVIEW_ADMIN_PASSWORD from the
deployment env. Idempotent upsert of a verified admin user plus a sample
client subscription so /app/admin/suscripciones is walkable.

Credentials must never land in client bundles or PR comments — store them
in the agent store and/or Vercel Preview env only.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4


def _is_preview() -> bool:
    return (os.environ.get("VERCEL_ENV") or "").strip().lower() == "preview"


def ensure_preview_admin() -> None:
    """Upsert preview admin (+ sample subscription). No-op outside preview."""
    if not _is_preview():
        return

    email = (os.environ.get("KOI_PREVIEW_ADMIN_EMAIL") or "").strip().lower()
    password = os.environ.get("KOI_PREVIEW_ADMIN_PASSWORD") or ""
    if not email or not password:
        return

    # Lazy imports: keep module importable for unit tests without apps/api on path.
    from sqlalchemy import create_engine, text

    from app.core.config import get_settings, to_sync_database_url
    from app.core.security import hash_password

    settings = get_settings()
    engine = create_engine(to_sync_database_url(settings.database_url))
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=30)
    demo_email = "preview-client@koicloud.test"

    try:
        with engine.begin() as connection:
            admin_row = connection.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email},
            ).first()
            password_hash = hash_password(password)
            if admin_row is None:
                connection.execute(
                    text(
                        """
                        INSERT INTO users (
                            id, email, password_hash, full_name, role, status,
                            email_verified_at
                        )
                        VALUES (
                            :id, :email, :password_hash, :full_name, 'admin',
                            'active', :verified_at
                        )
                        """
                    ),
                    {
                        "id": str(uuid4()),
                        "email": email,
                        "password_hash": password_hash,
                        "full_name": "Preview Admin",
                        "verified_at": now,
                    },
                )
            else:
                connection.execute(
                    text(
                        """
                        UPDATE users
                        SET password_hash = :password_hash,
                            role = 'admin',
                            status = 'active',
                            email_verified_at = COALESCE(email_verified_at, :verified_at)
                        WHERE email = :email
                        """
                    ),
                    {
                        "email": email,
                        "password_hash": password_hash,
                        "verified_at": now,
                    },
                )

            client_row = connection.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": demo_email},
            ).first()
            if client_row is None:
                client_id = str(uuid4())
                connection.execute(
                    text(
                        """
                        INSERT INTO users (
                            id, email, password_hash, full_name, role, status,
                            email_verified_at
                        )
                        VALUES (
                            :id, :email, :password_hash, :full_name, 'client',
                            'active', :verified_at
                        )
                        """
                    ),
                    {
                        "id": client_id,
                        "email": demo_email,
                        "password_hash": hash_password(password),
                        "full_name": "Preview Client",
                        "verified_at": now,
                    },
                )
            else:
                client_id = str(client_row[0])

            plan = connection.execute(
                text("SELECT id FROM plans WHERE id = 'micro' LIMIT 1")
            ).first()
            if plan is not None:
                existing_sub = connection.execute(
                    text(
                        """
                        SELECT id FROM subscriptions
                        WHERE user_id = :user_id AND plan_id = 'micro'
                        LIMIT 1
                        """
                    ),
                    {"user_id": client_id},
                ).first()
                if existing_sub is None:
                    connection.execute(
                        text(
                            """
                            INSERT INTO subscriptions (
                                id, user_id, plan_id, status,
                                current_period_start, current_period_end,
                                cancel_at_period_end
                            )
                            VALUES (
                                :id, :user_id, 'micro', 'active',
                                :start, :end, false
                            )
                            """
                        ),
                        {
                            "id": str(uuid4()),
                            "user_id": client_id,
                            "start": now,
                            "end": period_end,
                        },
                    )
    finally:
        engine.dispose()

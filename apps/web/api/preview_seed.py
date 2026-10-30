"""Preview-only admin seed for Vercel (never production).

Requires all of:
  - VERCEL_ENV=preview
  - KOI_PREVIEW_SEED=1 (explicit opt-in)
  - DATABASE_URL that does not look like production
  - At least one of:
      KOI_PREVIEW_ADMIN_EMAIL / KOI_PREVIEW_ADMIN_PASSWORD
      KOI_GATE_ADMIN_EMAIL / KOI_GATE_ADMIN_PASSWORD  (dedicated gate walk admin)

Idempotent upsert of verified admin(s) plus a sample client subscription
so /app/admin/subscriptions is walkable. The demo client gets its own
random password (never an admin password).

Credentials must never land in client bundles or PR comments — store them
in the agent store and/or Vercel Preview env only.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

# Host / path markers that mean "this is not a preview scratch DB".
_PROD_DB_MARKERS = (
    "prod",
    "production",
    "koicloud.dev",
    "primary.",
    "-pooler.prod",
)


def _is_preview() -> bool:
    return (os.environ.get("VERCEL_ENV") or "").strip().lower() == "preview"


def _seed_opt_in() -> bool:
    return (os.environ.get("KOI_PREVIEW_SEED") or "").strip() == "1"


def _database_url_looks_like_production(url: str) -> bool:
    """Heuristic refuse: never seed against a URL that smells like prod."""
    raw = (url or "").strip()
    if not raw:
        return True
    normalized = raw.lower()
    for prefix in (
        "postgresql+asyncpg://",
        "postgresql+psycopg://",
        "postgres+asyncpg://",
    ):
        if normalized.startswith(prefix):
            normalized = "postgresql://" + normalized[len(prefix) :]
            break
    parsed = urlparse(normalized)
    host = parsed.hostname or ""
    path = (parsed.path or "").lstrip("/")
    haystack = f"{host}/{path}"
    return any(marker in haystack for marker in _PROD_DB_MARKERS)


def _admin_pairs() -> list[tuple[str, str, str]]:
    """Collect (email, password, full_name) pairs from preview env."""
    pairs: list[tuple[str, str, str]] = []
    preview_email = (os.environ.get("KOI_PREVIEW_ADMIN_EMAIL") or "").strip().lower()
    preview_password = os.environ.get("KOI_PREVIEW_ADMIN_PASSWORD") or ""
    if preview_email and preview_password:
        pairs.append((preview_email, preview_password, "Preview Admin"))
    gate_email = (os.environ.get("KOI_GATE_ADMIN_EMAIL") or "").strip().lower()
    gate_password = os.environ.get("KOI_GATE_ADMIN_PASSWORD") or ""
    if gate_email and gate_password:
        pairs.append((gate_email, gate_password, "Gate Test Admin"))
    return pairs


def _upsert_admin(
    connection: Any,
    *,
    email: str,
    password_hash: str,
    full_name: str,
    verified_at: datetime,
) -> None:
    from sqlalchemy import text

    admin_row = connection.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email},
    ).first()
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
                "full_name": full_name,
                "verified_at": verified_at,
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
                "verified_at": verified_at,
            },
        )


def ensure_preview_admin() -> None:
    """Upsert preview/gate admins (+ sample subscription). No-op when unsafe."""
    if not _is_preview():
        return
    if not _seed_opt_in():
        return

    pairs = _admin_pairs()
    if not pairs:
        return

    # Lazy imports: keep module importable for unit tests without apps/api on path.
    from sqlalchemy import create_engine, text

    from app.core.config import get_settings, to_sync_database_url
    from app.core.security import hash_password

    settings = get_settings()
    if _database_url_looks_like_production(settings.database_url):
        return

    engine = create_engine(to_sync_database_url(settings.database_url))
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=30)
    demo_email = "preview-client@koicloud.test"
    # Distinct from every admin password.
    client_password = secrets.token_urlsafe(24)

    try:
        with engine.begin() as connection:
            for email, password, full_name in pairs:
                _upsert_admin(
                    connection,
                    email=email,
                    password_hash=hash_password(password),
                    full_name=full_name,
                    verified_at=now,
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
                        "password_hash": hash_password(client_password),
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

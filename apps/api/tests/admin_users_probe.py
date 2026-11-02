from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.db import SessionLocal
from app.core.enums import UserRole, UserStatus
from app.core.models import User
from app.core.security import hash_password
from tests.db_reset import reset_auth_tables

ADMIN_EMAIL = "admin-pages@koicloud.test"
OLDEST_EMAIL = "oldest-page@koicloud.test"
SUSPEND_EMAIL = "suspend-me@koicloud.test"
PASSWORD = "Sup3rSegura!2026"
PAGE_COUNT = 51


def seed_admin_user_pages() -> str:
    """Seed one admin plus enough accounts for a second page of GET /admin/users."""
    asyncio.run(_seed())
    return json.dumps(
        {
            "email": ADMIN_EMAIL,
            "password": PASSWORD,
            "oldest": OLDEST_EMAIL,
            "suspend": SUSPEND_EMAIL,
        }
    )


async def _seed() -> None:
    reset_auth_tables()
    password_hash = hash_password(PASSWORD)
    base = datetime(2026, 3, 1, tzinfo=UTC)
    async with SessionLocal() as session:
        for index in range(PAGE_COUNT):
            if index == 0:
                email = OLDEST_EMAIL
                full_name = "Cuenta más antigua"
                role = UserRole.CLIENT
            elif index == PAGE_COUNT - 2:
                email = SUSPEND_EMAIL
                full_name = "Cuenta a suspender"
                role = UserRole.CLIENT
            elif index == PAGE_COUNT - 1:
                email = ADMIN_EMAIL
                full_name = "Admin de páginas"
                role = UserRole.ADMIN
            else:
                email = f"page-extra-{index:03d}@koicloud.test"
                full_name = f"Cuenta extra {index:03d}"
                role = UserRole.CLIENT
            session.add(
                User(
                    id=UUID(int=index + 1),
                    email=email,
                    password_hash=password_hash,
                    full_name=full_name,
                    role=role,
                    status=UserStatus.ACTIVE,
                    email_verified_at=base,
                    created_at=base + timedelta(seconds=index),
                )
            )
        await session.commit()

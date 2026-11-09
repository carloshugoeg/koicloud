from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select, text

from app.core.db import SessionLocal, engine
from app.core.enums import EmailTokenKind, SubscriptionStatus, UserRole, UserStatus
from app.core.models import AuditEvent, Subscription, User
from app.core.security import hash_password
from app.main import app
from app.modules.admin import AdminService
from app.modules.auth import AuthService
from app.schemas import SuspendUserRequest
from tests.db_reset import reset_auth_tables

PASSWORD = "Sup3rSegura!2026"


def _make_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _register_and_verify(client: AsyncClient, email: str) -> UUID:
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": "Admin Fixture"},
    )
    assert registered.status_code == 201
    user_id = UUID(registered.json()["user_id"])
    token = await AuthService.issue_email_token(user_id, EmailTokenKind.VERIFY_EMAIL)
    verified = await client.post("/api/v1/auth/verify", json={"token": token})
    assert verified.status_code == 200
    return user_id


async def _login(client: AsyncClient, email: str) -> str:
    logged_in = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert logged_in.status_code == 200
    return logged_in.json()["access_token"]


async def _promote(user_id: UUID, role: UserRole) -> None:
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        assert user is not None
        user.role = role
        await session.commit()


async def test_admin_list_users_returns_plan_and_cursor() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-list@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-list@koicloud.dev")

        response = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["next_cursor"] is None
    assert len(body["users"]) >= 1
    for user in body["users"]:
        assert "active_subscription_plan" in user
        assert user["status"] in {"active", "suspended"}

    listed = await AdminService.list_users()
    assert listed.next_cursor is None
    assert len(listed.users) == len(body["users"])


async def test_admin_list_users_returns_registered_accounts_not_fixtures() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "qa-admin@koicloud.test")
        await _promote(admin_id, UserRole.ADMIN)
        await _register_and_verify(client, "qa+1@koicloud.test")
        token = await _login(client, "qa-admin@koicloud.test")

        response = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()
    emails = {user["email"] for user in body["users"]}
    assert emails == {"qa-admin@koicloud.test", "qa+1@koicloud.test"}
    qa_account = next(user for user in body["users"] if user["email"] == "qa+1@koicloud.test")
    assert qa_account["full_name"] == "Admin Fixture"
    assert qa_account["active_subscription_plan"] is None
    assert qa_account["status"] == "active"
    assert "carlos@koicloud.dev" not in emails
    assert "suspended@koicloud.dev" not in emails


async def test_non_admin_receives_admin_only() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        await _register_and_verify(client, "client-admin@koicloud.dev")
        token = await _login(client, "client-admin@koicloud.dev")
        response = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    assert response.json()["code"] == "admin_only"


_SECRET_USER_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "token",
        "access_token",
        "refresh_token",
        "jwt",
        "secret",
        "db_password_encrypted",
    }
)


async def test_admin_list_users_superadmin_panel_fields() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        owner_id = await _register_and_verify(client, "owner-panel@koicloud.test")
        owner_token = await _login(client, "owner-panel@koicloud.test")
        created = await client.post(
            "/api/v1/ponds",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"name": "panel-demo"},
        )
        assert created.status_code == 202

        admin_id = await _register_and_verify(client, "admin-panel@koicloud.test")
        await _promote(admin_id, UserRole.ADMIN)
        admin_token = await _login(client, "admin-panel@koicloud.test")

        response = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert "next_cursor" in body
    by_email = {user["email"]: user for user in body["users"]}
    assert set(by_email) == {"owner-panel@koicloud.test", "admin-panel@koicloud.test"}

    owner = by_email["owner-panel@koicloud.test"]
    assert owner["email"] == "owner-panel@koicloud.test"
    assert owner["email_verified"] is True
    assert isinstance(owner["created_at"], str) and owner["created_at"]
    assert "active_subscription_plan" in owner
    assert owner["ponds_count"] == 1
    assert owner["id"] == str(owner_id)

    admin_row = by_email["admin-panel@koicloud.test"]
    assert admin_row["ponds_count"] == 0
    assert admin_row["email_verified"] is True

    for user in body["users"]:
        assert _SECRET_USER_KEYS.isdisjoint(user.keys())
        assert "password_hash" not in user
        lowered = {key.lower() for key in user}
        assert not any("token" in key or "secret" in key or "password" in key for key in lowered)


async def test_admin_list_users_anonymous_receives_401() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        response = await client.get("/api/v1/admin/users")

    assert response.status_code == 401
    assert response.json()["code"] == "token_invalid"


async def test_admin_list_users_non_admin_forbidden_for_panel() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        await _register_and_verify(client, "client-panel@koicloud.test")
        token = await _login(client, "client-panel@koicloud.test")
        response = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    assert response.json()["code"] == "admin_only"


async def test_suspend_and_reactivate_user() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-suspend@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-suspend@koicloud.dev")
        target_id = await _register_and_verify(client, "target-suspend@koicloud.dev")
        headers = {"Authorization": f"Bearer {token}"}

        mismatch = await client.post(
            f"/api/v1/admin/users/{target_id}/suspend",
            headers=headers,
            json={"confirm_text": "no"},
        )
        assert mismatch.status_code == 409

        suspended = await client.post(
            f"/api/v1/admin/users/{target_id}/suspend",
            headers=headers,
            json={"confirm_text": "SUSPENDER"},
        )
        assert suspended.status_code == 200
        suspended_user = suspended.json()["user"]
        assert suspended_user["id"] == str(target_id)
        assert suspended_user["status"] == "suspended"

        reactivated = await client.post(
            f"/api/v1/admin/users/{target_id}/reactivate",
            headers=headers,
        )
        assert reactivated.status_code == 200
        assert reactivated.json()["user"]["id"] == str(target_id)
        assert reactivated.json()["user"]["status"] == "active"

    via_service = await AdminService.suspend_user(
        target_id, SuspendUserRequest(confirm_text="SUSPENDER")
    )
    assert via_service.user.status == UserStatus.SUSPENDED
    cleared = await AdminService.reactivate_user(target_id)
    assert cleared.user.status == UserStatus.ACTIVE


async def test_suspend_user_stores_trimmed_reason_in_audit_metadata() -> None:
    reset_auth_tables()
    async with SessionLocal() as session:
        await session.execute(text("DELETE FROM audit_events"))
        await session.commit()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-reason@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-reason@koicloud.dev")
        target_id = await _register_and_verify(client, "target-reason@koicloud.dev")

        response = await client.post(
            f"/api/v1/admin/users/{target_id}/suspend",
            headers={"Authorization": f"Bearer {token}"},
            json={"confirm_text": "SUSPENDER", "reason": "  abuso de recursos  "},
        )
        assert response.status_code == 200
        assert response.json()["user"]["status"] == "suspended"

        audit = await client.get(
            "/api/v1/admin/audit",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert audit.status_code == 200
        match = next(
            event
            for event in audit.json()["events"]
            if event["action"] == "suspend_user" and event["target_id"] == str(target_id)
        )
        assert match["metadata"]["reason"] == "abuso de recursos"
        assert match["actor_user_id"] == str(admin_id)
        assert match["actor_kind"] == "admin"

    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(AuditEvent).where(
                    AuditEvent.action == "suspend_user",
                    AuditEvent.target_id == target_id,
                )
            )
        ).scalar_one()
        assert row.event_metadata == {"reason": "abuso de recursos"}


async def test_suspend_user_omits_reason_from_metadata_when_absent() -> None:
    reset_auth_tables()
    async with SessionLocal() as session:
        await session.execute(text("DELETE FROM audit_events"))
        await session.commit()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-noreason@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-noreason@koicloud.dev")
        target_id = await _register_and_verify(client, "target-noreason@koicloud.dev")

        response = await client.post(
            f"/api/v1/admin/users/{target_id}/suspend",
            headers={"Authorization": f"Bearer {token}"},
            json={"confirm_text": "SUSPENDER"},
        )
        assert response.status_code == 200

    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(AuditEvent).where(
                    AuditEvent.action == "suspend_user",
                    AuditEvent.target_id == target_id,
                )
            )
        ).scalar_one()
        assert row.event_metadata == {}


async def test_login_rejects_suspended_account() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        user_id = await _register_and_verify(client, "suspended-login@koicloud.dev")
        async with SessionLocal() as session:
            user = await session.get(User, user_id)
            assert user is not None
            user.status = UserStatus.SUSPENDED
            await session.commit()

        suspended = await client.post(
            "/api/v1/auth/login",
            json={"email": "suspended-login@koicloud.dev", "password": PASSWORD},
        )

    assert suspended.status_code == 403
    assert suspended.json()["code"] == "account_suspended"


async def test_suspend_user_rejects_reason_over_500_chars() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-longreason@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-longreason@koicloud.dev")
        target_id = await _register_and_verify(client, "target-longreason@koicloud.dev")

        response = await client.post(
            f"/api/v1/admin/users/{target_id}/suspend",
            headers={"Authorization": f"Bearer {token}"},
            json={"confirm_text": "SUSPENDER", "reason": "x" * 501},
        )

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "string_too_long"


async def test_suspend_user_accepts_reason_exactly_500_chars() -> None:
    reset_auth_tables()
    async with SessionLocal() as session:
        await session.execute(text("DELETE FROM audit_events"))
        await session.commit()

    reason = "x" * 500
    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-exact500@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-exact500@koicloud.dev")
        target_id = await _register_and_verify(client, "target-exact500@koicloud.dev")

        response = await client.post(
            f"/api/v1/admin/users/{target_id}/suspend",
            headers={"Authorization": f"Bearer {token}"},
            json={"confirm_text": "SUSPENDER", "reason": reason},
        )
        assert response.status_code == 200
        assert response.json()["user"]["status"] == "suspended"

    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(AuditEvent).where(
                    AuditEvent.action == "suspend_user",
                    AuditEvent.target_id == target_id,
                )
            )
        ).scalar_one()
        stored = row.event_metadata["reason"]
        assert stored == reason
        assert len(stored) == 500


async def test_suspend_user_accepts_padded_reason_that_trims_to_500() -> None:
    reset_auth_tables()
    async with SessionLocal() as session:
        await session.execute(text("DELETE FROM audit_events"))
        await session.commit()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-padded500@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-padded500@koicloud.dev")
        target_id = await _register_and_verify(client, "target-padded500@koicloud.dev")

        response = await client.post(
            f"/api/v1/admin/users/{target_id}/suspend",
            headers={"Authorization": f"Bearer {token}"},
            json={"confirm_text": "SUSPENDER", "reason": "  " + ("x" * 500) + "  "},
        )
        assert response.status_code == 200
        assert response.json()["user"]["status"] == "suspended"

    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(AuditEvent).where(
                    AuditEvent.action == "suspend_user",
                    AuditEvent.target_id == target_id,
                )
            )
        ).scalar_one()
        stored = row.event_metadata["reason"]
        assert stored == "x" * 500
        assert len(stored) == 500


async def test_non_admin_post_suspend_receives_admin_only() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        await _register_and_verify(client, "client-post-suspend@koicloud.dev")
        token = await _login(client, "client-post-suspend@koicloud.dev")
        target_id = await _register_and_verify(client, "target-post-suspend@koicloud.dev")
        response = await client.post(
            f"/api/v1/admin/users/{target_id}/suspend",
            headers={"Authorization": f"Bearer {token}"},
            json={"confirm_text": "SUSPENDER"},
        )

    assert response.status_code == 403
    assert response.json()["code"] == "admin_only"


async def test_unauthenticated_post_suspend_receives_token_invalid() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        target_id = await _register_and_verify(client, "target-unauth-suspend@koicloud.dev")
        response = await client.post(
            f"/api/v1/admin/users/{target_id}/suspend",
            json={"confirm_text": "SUSPENDER"},
        )

    assert response.status_code == 401
    assert response.json()["code"] == "token_invalid"


async def test_suspend_missing_user_returns_user_not_found() -> None:
    reset_auth_tables()

    async with _make_client() as client:
        admin_id = await _register_and_verify(client, "admin-missing@koicloud.dev")
        await _promote(admin_id, UserRole.ADMIN)
        token = await _login(client, "admin-missing@koicloud.dev")
        missing_id = uuid4()

        response = await client.post(
            f"/api/v1/admin/users/{missing_id}/suspend",
            headers={"Authorization": f"Bearer {token}"},
            json={"confirm_text": "SUSPENDER", "reason": "cuenta fantasma"},
        )

    assert response.status_code == 404
    assert response.json()["code"] == "user_not_found"


async def _seed_users(count: int, *, tie_at: datetime | None = None) -> None:
    reset_auth_tables()
    password_hash = hash_password(PASSWORD)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    async with SessionLocal() as session:
        users: list[User] = []
        for index in range(count):
            created_at = tie_at if tie_at is not None else base + timedelta(seconds=index)
            user = User(
                id=UUID(int=index + 1),
                email=f"page-{index:03d}@koicloud.test",
                password_hash=password_hash,
                full_name=f"Cuenta {index:03d}",
                role=UserRole.ADMIN if index == 0 else UserRole.CLIENT,
                status=UserStatus.ACTIVE,
                email_verified_at=base,
                created_at=created_at,
            )
            session.add(user)
            users.append(user)
        await session.flush()
        for index, user in enumerate(users):
            if index % 10 == 0:
                session.add(
                    Subscription(
                        user_id=user.id,
                        plan_id="pro",
                        status=SubscriptionStatus.ACTIVE,
                        current_period_start=base,
                        current_period_end=base + timedelta(days=30),
                        cancel_at_period_end=False,
                    )
                )
            elif index % 10 == 1:
                session.add(
                    Subscription(
                        user_id=user.id,
                        plan_id="micro",
                        status=SubscriptionStatus.CANCELED,
                        current_period_start=base,
                        current_period_end=base + timedelta(days=30),
                        cancel_at_period_end=False,
                    )
                )
        await session.commit()


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    token = await _login(client, "page-000@koicloud.test")
    return {"Authorization": f"Bearer {token}"}


async def test_admin_list_users_returns_three_pages_for_120_users() -> None:
    await _seed_users(120)

    async with _make_client() as client:
        headers = await _admin_headers(client)
        first = await client.get("/api/v1/admin/users", headers=headers)

    assert first.status_code == 200
    body = first.json()
    assert len(body["users"]) == 50
    assert isinstance(body["next_cursor"], str)
    assert body["next_cursor"]
    for user in body["users"]:
        assert user["id"] not in body["next_cursor"]
    by_email = {user["email"]: user for user in body["users"]}
    assert by_email["page-110@koicloud.test"]["active_subscription_plan"] == "pro"
    assert by_email["page-111@koicloud.test"]["active_subscription_plan"] is None

    pages = [body["users"]]
    cursor = body["next_cursor"]
    async with _make_client() as client:
        headers = await _admin_headers(client)
        while cursor is not None:
            page = await client.get(
                "/api/v1/admin/users",
                headers=headers,
                params={"cursor": cursor},
            )
            assert page.status_code == 200
            payload = page.json()
            pages.append(payload["users"])
            cursor = payload["next_cursor"]

    sizes = [len(page) for page in pages]
    assert sizes == [50, 50, 20]
    emails = [user["email"] for page in pages for user in page]
    assert emails == [f"page-{index:03d}@koicloud.test" for index in range(119, -1, -1)]
    assert len(emails) == len(set(emails))


async def test_admin_list_users_rejects_limit_above_200() -> None:
    await _seed_users(120)

    async with _make_client() as client:
        headers = await _admin_headers(client)
        over = await client.get("/api/v1/admin/users", headers=headers, params={"limit": 201})
        assert over.status_code == 422

        zero = await client.get("/api/v1/admin/users", headers=headers, params={"limit": 0})
        assert zero.status_code == 422

        wide = await client.get("/api/v1/admin/users", headers=headers, params={"limit": 200})
        assert wide.status_code == 200
        assert len(wide.json()["users"]) == 120
        assert wide.json()["next_cursor"] is None

        bad_cursor = await client.get(
            "/api/v1/admin/users",
            headers=headers,
            params={"cursor": "not-a-cursor"},
        )
        assert bad_cursor.status_code == 422


async def test_admin_list_users_loads_plans_in_one_query() -> None:
    await _seed_users(120)
    statements: list[str] = []

    def before_cursor_execute(
        _conn: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
    try:
        async with _make_client() as client:
            headers = await _admin_headers(client)
            statements.clear()
            response = await client.get("/api/v1/admin/users", headers=headers)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", before_cursor_execute)

    assert response.status_code == 200
    body = response.json()
    assert any(user["active_subscription_plan"] == "pro" for user in body["users"])
    subscription_sql = [sql for sql in statements if "subscriptions" in sql.lower()]
    assert len(subscription_sql) == 1


async def test_admin_list_users_orders_equal_timestamps_by_id_desc() -> None:
    shared = datetime(2026, 6, 1, tzinfo=UTC)
    await _seed_users(2, tie_at=shared)

    async with _make_client() as client:
        headers = await _admin_headers(client)
        first = await client.get("/api/v1/admin/users", headers=headers, params={"limit": 1})
        assert first.status_code == 200
        page = first.json()
        assert [user["id"] for user in page["users"]] == [str(UUID(int=2))]
        assert page["next_cursor"]

        second = await client.get(
            "/api/v1/admin/users",
            headers=headers,
            params={"limit": 1, "cursor": page["next_cursor"]},
        )
        assert second.status_code == 200
        rest = second.json()
        assert [user["id"] for user in rest["users"]] == [str(UUID(int=1))]
        assert rest["next_cursor"] is None

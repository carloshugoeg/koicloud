from __future__ import annotations

import secrets
from datetime import timedelta
from urllib.parse import quote
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthContext
from app.core.config import Settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.enums import (
    JobStatus,
    JobType,
    NodeStatus,
    PondDesiredState,
    PondObservedState,
    SubscriptionStatus,
    UserRole,
    UserStatus,
)
from app.core.errors import AppError, ErrorCode
from app.core.models import Job, Node, Plan, Pond, PondStatus, Subscription, User
from app.core.security import hash_password, hash_token
from app.core.time import utc_now
from app.schemas import ConnectionOut, JobOut, PondOut


def _database_name(pond_name: str) -> str:
    return pond_name.replace("-", "_")


def pond_to_out(pond: Pond, status: PondStatus) -> PondOut:
    return PondOut(
        id=pond.id,
        user_id=pond.user_id,
        plan_id=pond.plan_id,
        node_id=pond.node_id,
        name=pond.name,
        engine_version=pond.engine_version,
        desired_state=pond.desired_state,
        observed_state=status.observed_state,
        host_port=pond.host_port,
        healthy=status.healthy,
        created_at=pond.created_at,
        last_restore_at=pond.last_restore_at,
        last_error=status.last_error,
    )


def job_to_out(job: Job) -> JobOut:
    return JobOut(
        id=job.id,
        type=job.type,
        pond_id=job.pond_id,
        node_id=job.node_id,
        status=job.status,
        attempts=job.attempts,
        created_at=job.created_at,
        claimed_at=job.claimed_at,
        completed_at=job.completed_at,
        last_error=job.last_error,
    )


def connection_for(pond: Pond, node: Node, password: str) -> ConnectionOut:
    database = _database_name(pond.name)
    username = "postgres"
    encoded = quote(password, safe="")
    return ConnectionOut(
        host=node.public_host,
        port=pond.host_port,
        database=database,
        username=username,
        password=password,
        uri=f"postgresql://{username}:{encoded}@{node.public_host}:{pond.host_port}/{database}",
    )


class PondService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def list_for_user(self, actor: AuthContext) -> list[PondOut]:
        rows = await self.session.execute(self._owned_query(UUID(actor.user_id)))
        return [pond_to_out(pond, status) for pond, status in rows.all()]

    async def get_owned(self, actor: AuthContext, pond_id: UUID) -> tuple[Pond, PondStatus]:
        row = (
            await self.session.execute(
                self._owned_query(UUID(actor.user_id)).where(Pond.id == pond_id)
            )
        ).first()
        if row is None:
            exists = await self.session.get(Pond, pond_id)
            if exists is None or exists.desired_state == PondDesiredState.DELETED:
                raise AppError(ErrorCode.POND_NOT_FOUND)
            raise AppError(ErrorCode.NOT_OWNER)
        return row[0], row[1]

    async def get_owned_by_name(self, actor: AuthContext, name: str) -> tuple[Pond, PondStatus]:
        row = (
            await self.session.execute(
                self._owned_query(UUID(actor.user_id)).where(Pond.name == name)
            )
        ).first()
        if row is None:
            raise AppError(ErrorCode.POND_NOT_FOUND)
        return row[0], row[1]

    async def create(
        self, actor: AuthContext, *, name: str, engine_version: str
    ) -> tuple[PondOut, JobOut]:
        user = await self.ensure_actor(actor)
        node = await self.ensure_live_node()
        subscription = await self.ensure_subscription(user)
        await self._assert_name_free(user.id, name)
        await self._assert_quota(user.id, subscription.plan_id)

        password = secrets.token_urlsafe(18)
        try:
            pond = Pond(
                user_id=user.id,
                plan_id=subscription.plan_id,
                node_id=node.id,
                name=name,
                engine_version=engine_version,
                desired_state=PondDesiredState.RUNNING,
                host_port=await self._next_port(),
                db_password_encrypted=encrypt_secret(password),
            )
            self.session.add(pond)
            await self.session.flush()
            status = PondStatus(
                pond_id=pond.id,
                observed_state=PondObservedState.PENDING,
                healthy=False,
            )
            job = Job(
                type=JobType.CREATE_POND,
                pond_id=pond.id,
                node_id=node.id,
                status=JobStatus.QUEUED,
                payload={
                    "name": pond.name,
                    "host_port": pond.host_port,
                    "memory_mb": 512,
                    "cpus": 0.5,
                    "db_password_plain": password,
                    "image": "postgres:16-alpine",
                },
            )
            self.session.add_all([status, job])
            await self.session.flush()
        except IntegrityError as exc:
            raise self._translate_integrity(exc) from exc
        return pond_to_out(pond, status), job_to_out(job)

    async def connection_for_owned(self, actor: AuthContext, pond_id: UUID) -> ConnectionOut:
        pond, _status = await self.get_owned(actor, pond_id)
        node = await self.session.get(Node, pond.node_id)
        if node is None:
            raise AppError(ErrorCode.NODE_UNAVAILABLE)
        return connection_for(pond, node, decrypt_secret(pond.db_password_encrypted))

    async def delete(self, actor: AuthContext, pond_id: UUID) -> tuple[PondOut, list[JobOut]]:
        pond, status = await self.get_owned(actor, pond_id)
        await self._assert_no_active_job(pond.id)

        pond.desired_state = PondDesiredState.DELETED
        status.observed_state = PondObservedState.DELETING
        status.healthy = False
        status.updated_at = utc_now()

        job = Job(
            type=JobType.DELETE_POND,
            pond_id=pond.id,
            node_id=pond.node_id,
            status=JobStatus.QUEUED,
            payload=self._agent_payload(pond),
        )
        self.session.add(job)
        await self.session.flush()
        return pond_to_out(pond, status), [job_to_out(job)]

    async def retry_failed(self, actor: AuthContext, pond_id: UUID) -> JobOut:
        pond, status = await self.get_owned(actor, pond_id)
        await self._assert_no_active_job(pond.id)

        failed = (
            await self.session.execute(
                select(Job)
                .where(Job.pond_id == pond.id, Job.status == JobStatus.FAILED)
                .order_by(Job.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if failed is None:
            raise AppError(
                ErrorCode.POND_NOT_FOUND,
                message="No hay un job fallido para reintentar en este pond",
            )

        job = Job(
            type=failed.type,
            pond_id=pond.id,
            node_id=pond.node_id,
            status=JobStatus.QUEUED,
            payload=dict(failed.payload or self._agent_payload(pond)),
        )
        status.observed_state = PondObservedState.PENDING
        status.healthy = False
        status.last_error = None
        status.updated_at = utc_now()
        if failed.type == JobType.CREATE_POND:
            pond.desired_state = PondDesiredState.RUNNING
        elif failed.type == JobType.DELETE_POND:
            pond.desired_state = PondDesiredState.DELETED
            status.observed_state = PondObservedState.DELETING

        self.session.add(job)
        await self.session.flush()
        return job_to_out(job)

    def _agent_payload(self, pond: Pond) -> dict[str, object]:
        password = decrypt_secret(pond.db_password_encrypted)
        return {
            "name": pond.name,
            "host_port": pond.host_port,
            "memory_mb": 512,
            "cpus": 0.5,
            "db_password_plain": password,
            "image": "postgres:16-alpine",
        }

    async def _assert_no_active_job(self, pond_id: UUID) -> None:
        active = (
            await self.session.execute(
                select(Job.id).where(
                    Job.pond_id == pond_id,
                    Job.status.in_((JobStatus.QUEUED, JobStatus.RUNNING)),
                )
            )
        ).scalar_one_or_none()
        if active is not None:
            raise AppError(ErrorCode.POND_BUSY)

    async def ensure_actor(self, actor: AuthContext) -> User:
        user_id = UUID(actor.user_id)
        user = await self.session.get(User, user_id)
        if user is not None:
            return user
        user = User(
            id=user_id,
            email=actor.email,
            password_hash=hash_password(secrets.token_urlsafe(24)),
            full_name=actor.email.split("@", 1)[0].replace(".", " ").title() or actor.email,
            role=actor.role if isinstance(actor.role, UserRole) else UserRole.CLIENT,
            status=actor.status if isinstance(actor.status, UserStatus) else UserStatus.ACTIVE,
            email_verified_at=utc_now(),
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def ensure_live_node(self) -> Node:
        node = await self._upsert_node()
        if node.status != NodeStatus.ALIVE:
            raise AppError(ErrorCode.NODE_UNAVAILABLE)
        if node.last_seen_at is None:
            raise AppError(ErrorCode.NODE_UNAVAILABLE)
        age = utc_now() - node.last_seen_at
        if age > timedelta(seconds=self.settings.node_stale_seconds):
            raise AppError(ErrorCode.NODE_UNAVAILABLE)
        return node

    async def ensure_subscription(self, user: User) -> Subscription:
        active = (
            await self.session.execute(
                select(Subscription)
                .where(
                    Subscription.user_id == user.id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.current_period_end > utc_now(),
                )
                .order_by(Subscription.current_period_end.desc())
            )
        ).scalar_one_or_none()
        if active is not None:
            return active
        if not self.settings.auto_micro_subscription:
            raise AppError(ErrorCode.PLAN_REQUIRED)
        plan = await self.session.get(Plan, "micro")
        if plan is None:
            raise AppError(ErrorCode.PLAN_REQUIRED)
        now = utc_now()
        subscription = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=now + timedelta(minutes=plan.validity_minutes),
        )
        self.session.add(subscription)
        await self.session.flush()
        return subscription

    async def _upsert_node(self) -> Node:
        settings = self.settings
        node = await self.session.get(Node, settings.node_id)
        token_hash = hash_token(settings.node_token)
        if node is None:
            node = Node(
                id=settings.node_id,
                public_host=settings.node_public_host,
                status=NodeStatus.ALIVE,
                capacity_ponds=20,
                last_seen_at=utc_now(),
                token_hash=token_hash,
            )
            self.session.add(node)
            await self.session.flush()
            return node
        node.public_host = settings.node_public_host
        node.token_hash = token_hash
        if node.last_seen_at is None:
            node.last_seen_at = utc_now()
            node.status = NodeStatus.ALIVE
        return node

    async def _assert_name_free(self, user_id: UUID, name: str) -> None:
        existing = (
            await self.session.execute(
                select(Pond.id).where(
                    Pond.user_id == user_id,
                    Pond.name == name,
                    Pond.desired_state != PondDesiredState.DELETED,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise AppError(ErrorCode.POND_NAME_TAKEN)

    async def _assert_quota(self, user_id: UUID, plan_id: str) -> None:
        plan = await self.session.get(Plan, plan_id)
        if plan is None:
            raise AppError(ErrorCode.PLAN_REQUIRED)
        count = (
            await self.session.execute(
                select(func.count())
                .select_from(Pond)
                .where(
                    Pond.user_id == user_id,
                    Pond.desired_state != PondDesiredState.DELETED,
                )
            )
        ).scalar_one()
        if count >= plan.max_ponds:
            raise AppError(ErrorCode.QUOTA_EXCEEDED)

    async def _next_port(self) -> int:
        # ponds_host_port_uk is global (includes soft-deleted rows), so skip all
        # occupied ports — not only non-deleted ones.
        used = set((await self.session.execute(select(Pond.host_port))).scalars())
        start = self.settings.pond_port_range_start
        end = self.settings.pond_port_range_end
        for port in range(start, end + 1):
            if port not in used:
                return port
        raise AppError(ErrorCode.NODE_UNAVAILABLE)

    def _owned_query(self, user_id: UUID) -> Select[tuple[Pond, PondStatus]]:
        return (
            select(Pond, PondStatus)
            .join(PondStatus, PondStatus.pond_id == Pond.id)
            .where(Pond.user_id == user_id, Pond.desired_state != PondDesiredState.DELETED)
            .order_by(Pond.created_at.desc())
        )

    def _translate_integrity(self, exc: IntegrityError) -> AppError:
        detail = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
        if "ponds_user_name_uk" in detail or "ponds_user_id_name" in detail:
            return AppError(ErrorCode.POND_NAME_TAKEN)
        if "ponds_host_port_uk" in detail:
            return AppError(ErrorCode.NODE_UNAVAILABLE)
        if "jobs_one_active" in detail:
            return AppError(ErrorCode.POND_BUSY)
        return AppError(ErrorCode.INTERNAL_ERROR)

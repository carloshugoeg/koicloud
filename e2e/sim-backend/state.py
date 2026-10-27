"""In-memory control plane for the preview sim.

Pond commands are a table. Create records provisioning, then applies start
in the same call because this process has no worker.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib.parse import quote

GATE_ADMIN_EMAIL = "gate-admin@koicloud.test"
GATE_USER_EMAIL = "gate-user@koicloud.test"
NODE_ID = "sim-node"
PORT_START = 15000
PORT_END = 15999
# Gate mint must stay valid ≥24h; sim-only TTL (not production agent-access).
MCP_TTL = timedelta(hours=36)
CONFIRM_TTL = timedelta(minutes=5)
PROMPT_SUMMARY = "Sos un asistente que opera KoiCloud (DBaaS académico)."

READ_ONLY_TOOLS = (
    "whoami",
    "list_ponds",
    "get_pond",
    "get_connection",
    "list_subscriptions",
    "list_backups",
)
MUTABLE_TOOLS = (
    "create_pond",
    "delete_pond",
    "restore_backup",
    "run_sql",
    "confirm_action",
    "cancel_confirmation",
)

WRITE_SQL = frozenset(
    {
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "truncate",
        "grant",
        "revoke",
        "copy",
        "vacuum",
        "comment",
    }
)

# desired, observed, healthy
POND_APPLY = {
    "start": ("running", "running", True),
    "stop": ("stopped", "stopped", False),
    "delete": ("deleted", "deleted", False),
}

PLANS: tuple[dict[str, object], ...] = (
    {
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
    {
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
    {
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
)
PLANS_BY_ID = {str(plan["id"]): plan for plan in PLANS}

CATALOG: dict[str, tuple[int, str]] = {
    "invalid_credentials": (401, "Correo o contraseña incorrectos"),
    "email_not_verified": (403, "Verificá tu correo antes de continuar"),
    "account_suspended": (403, "Cuenta suspendida por el administrador"),
    "token_expired": (401, "Sesión expirada, iniciá sesión otra vez"),
    "token_invalid": (401, "Token inválido o mal formado"),
    "email_taken": (409, "Ese correo ya está registrado"),
    "password_too_weak": (422, "La contraseña no cumple el mínimo de seguridad"),
    "plan_required": (409, "Necesitás una suscripción activa"),
    "quota_exceeded": (409, "Ya alcanzaste el máximo de ponds de tu plan"),
    "pond_name_taken": (409, "Ya existe un pond con ese nombre"),
    "pond_not_found": (404, "No existe el pond solicitado"),
    "confirmation_required": (409, "La acción requiere confirmación explícita"),
    "confirmation_not_found": (404, "El token de confirmación no existe"),
    "confirmation_expired": (410, "El token de confirmación ya expiró"),
    "confirmation_action_mismatch": (409, "El token no corresponde a esta acción"),
    "agent_disabled": (403, "El acceso agente está desactivado"),
    "agent_bad_credentials": (401, "Credenciales MCP inválidas"),
    "not_owner": (403, "No tenés acceso a este recurso"),
    "admin_only": (403, "Esta operación requiere rol administrador"),
    "sql_readonly_violation": (400, "La query es de escritura pero el modo es read"),
    "node_unavailable": (503, "No hay nodos disponibles en este momento"),
    # Sim-only MCP / restore codes (not production OpenAPI catalog).
    "method_not_found": (404, "Herramienta MCP desconocida"),
    "invalid_params": (400, "Falta un argumento requerido"),
    "backup_not_found": (404, "No existe el respaldo solicitado"),
}


class SimError(Exception):
    def __init__(
        self,
        code: str,
        *,
        status: int | None = None,
        message: str | None = None,
    ) -> None:
        spec_status, spec_message = CATALOG[code]
        self.code = code
        self.status = spec_status if status is None else status
        self.message = spec_message if message is None else message
        super().__init__(self.message)

    def body(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message, "request_id": None}


class ToolMiss(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(name)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def same_secret(left: str, right: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(left.encode()).digest(),
        hashlib.sha256(right.encode()).digest(),
    )


def _token_secret() -> bytes:
    raw = (os.environ.get("KOI_SIM_TOKEN_SECRET") or "koi-preview-sim-token").encode()
    return hashlib.sha256(raw).digest()


def issue_access_token(user: "User", *, hours: int = 12) -> str:
    """HMAC token with user claims — validates on any instance without Blob sessions."""
    import base64
    import json as _json

    exp = int((utcnow() + timedelta(hours=hours)).timestamp())
    payload = {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "full_name": user.full_name,
        "exp": exp,
    }
    body = (
        base64.urlsafe_b64encode(_json.dumps(payload, separators=(",", ":")).encode())
        .decode()
        .rstrip("=")
    )
    sig = hmac.new(_token_secret(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return f"sim2.{body}.{sig}"


def parse_access_token(token: str) -> tuple[str, dict[str, object]] | None:
    """Return (user_id, claims) for sim2 tokens, or (user_id, {}) for legacy sim tokens."""
    import base64
    import json as _json

    if token.startswith("sim2."):
        parts = token.split(".")
        if len(parts) != 3:
            return None
        _, body, sig = parts
        expected = hmac.new(_token_secret(), body.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(expected, sig):
            return None
        pad = "=" * (-len(body) % 4)
        try:
            payload = _json.loads(base64.urlsafe_b64decode(body + pad).decode())
        except (ValueError, _json.JSONDecodeError, UnicodeDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        user_id = payload.get("id")
        exp = payload.get("exp")
        if not isinstance(user_id, str) or not user_id:
            return None
        if not isinstance(exp, int) or exp < int(utcnow().timestamp()):
            return None
        return user_id, payload
    if not token.startswith("sim."):
        return None
    parts = token.split(".")
    if len(parts) != 4:
        return None
    _, user_id, exp_raw, sig = parts
    if not user_id or not exp_raw.isdigit():
        return None
    body = f"{user_id}.{exp_raw}"
    expected = hmac.new(_token_secret(), body.encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(expected, sig):
        return None
    if int(exp_raw) < int(utcnow().timestamp()):
        return None
    return user_id, {}


@dataclass
class User:
    id: str
    email: str
    password: str
    full_name: str
    role: str
    status: str
    email_verified: bool
    nit: str | None
    created_at: str
    verify_token: str | None = None


@dataclass
class Subscription:
    id: str
    user_id: str
    plan_id: str
    status: str
    current_period_start: str
    current_period_end: str
    cancel_at_period_end: bool
    invoice: dict[str, object]
    payment: dict[str, object]


@dataclass
class Pond:
    id: str
    user_id: str
    plan_id: str
    name: str
    engine_version: str
    desired_state: str
    observed_state: str
    host_port: int
    healthy: bool
    created_at: str
    db_password: str
    last_restore_at: str | None = None
    last_error: str | None = None


@dataclass
class Backup:
    id: str
    pond_id: str
    kind: str
    status: str
    storage_path: str
    size_bytes: int
    sha256: str
    created_at: str
    completed_at: str | None


@dataclass
class Pending:
    token: str
    user_id: str
    action: str
    payload: dict[str, str]
    summary: str
    expires_at: str
    consumed: bool = False


@dataclass
class Agent:
    user_id: str
    slug: str
    password: str
    enabled: bool
    rotated_at: str
    expires_at: str


def _user_out(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "nit": user.nit,
        "status": user.status,
        "email_verified": user.email_verified,
        "created_at": user.created_at,
    }


def _pond_out(pond: Pond) -> dict[str, object]:
    return {
        "id": pond.id,
        "user_id": pond.user_id,
        "plan_id": pond.plan_id,
        "node_id": NODE_ID,
        "name": pond.name,
        "engine_version": pond.engine_version,
        "desired_state": pond.desired_state,
        "observed_state": pond.observed_state,
        "host_port": pond.host_port,
        "healthy": pond.healthy,
        "created_at": pond.created_at,
        "last_restore_at": pond.last_restore_at,
        "last_error": pond.last_error,
    }


def _job(job_type: str, pond_id: str) -> dict[str, object]:
    moment = iso(utcnow())
    return {
        "id": str(uuid.uuid4()),
        "type": job_type,
        "pond_id": pond_id,
        "node_id": NODE_ID,
        "status": "succeeded",
        "attempts": 1,
        "created_at": moment,
        "claimed_at": moment,
        "completed_at": moment,
        "last_error": None,
    }


def _backup_out(row: Backup) -> dict[str, object]:
    return {
        "id": row.id,
        "pond_id": row.pond_id,
        "kind": row.kind,
        "status": row.status,
        "storage_path": row.storage_path,
        "size_bytes": row.size_bytes,
        "sha256": row.sha256,
        "created_at": row.created_at,
        "completed_at": row.completed_at,
    }


def _sub_out(row: Subscription) -> dict[str, object]:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "plan_id": row.plan_id,
        "status": row.status,
        "current_period_start": row.current_period_start,
        "current_period_end": row.current_period_end,
        "cancel_at_period_end": row.cancel_at_period_end,
    }


def _sql_is_write(query: str) -> bool:
    for part in query.split(";"):
        piece = part.strip()
        if not piece:
            continue
        token = piece.split(None, 1)[0].lower()
        if token in WRITE_SQL:
            return True
    return False


def _sql_result(query: str, *, write: bool) -> dict[str, object]:
    if write:
        return {
            "columns": [],
            "rows": [],
            "row_count": 1,
            "duration_ms": 1,
            "truncated": False,
        }
    normalized = " ".join(query.strip().rstrip(";").lower().split())
    if normalized in {"select 1", "select 1 as result"}:
        return {
            "columns": ["?column?"],
            "rows": [[1]],
            "row_count": 1,
            "duration_ms": 1,
            "truncated": False,
        }
    if "now()" in normalized:
        return {
            "columns": ["now"],
            "rows": [[iso(utcnow())]],
            "row_count": 1,
            "duration_ms": 1,
            "truncated": False,
        }
    return {
        "columns": ["result"],
        "rows": [["sim"]],
        "row_count": 1,
        "duration_ms": 1,
        "truncated": False,
    }


class State:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.users_by_email: dict[str, User] = {}
        self.users_by_id: dict[str, User] = {}
        # Ephemeral claim-hydrated actors (password=""). Never pickled / Blob-saved.
        self.claim_actors: dict[str, User] = {}
        self.sessions: dict[str, str] = {}
        self.subs: dict[str, Subscription] = {}
        self.ponds: dict[str, Pond] = {}
        self.backups: dict[str, list[Backup]] = {}
        self.sql_events: dict[str, list[dict[str, object]]] = {}
        self.pending: dict[str, Pending] = {}
        self.agents_by_user: dict[str, Agent] = {}
        self.agents_by_slug: dict[str, Agent] = {}
        self._next_port = PORT_START
        self._invoice_n = 0
        self._bind_tools()

    def _bind_tools(self) -> None:
        self._tools = {
            "whoami": self._tool_whoami,
            "list_ponds": self._tool_list_ponds,
            "get_pond": self._tool_get_pond,
            "get_connection": self._tool_get_connection,
            "list_subscriptions": self._tool_list_subscriptions,
            "list_backups": self._tool_list_backups,
            "create_pond": self._tool_create_pond,
            "delete_pond": self._tool_delete_pond,
            "restore_backup": self._tool_restore,
            "run_sql": self._tool_run_sql,
            "confirm_action": self._tool_confirm,
            "cancel_confirmation": self._tool_cancel,
        }

    def __getstate__(self) -> dict[str, object]:
        payload = dict(self.__dict__)
        payload.pop("_lock", None)
        payload.pop("_tools", None)
        payload.pop("claim_actors", None)
        # Never persist empty-password stubs into Blob.
        users = {
            user_id: user
            for user_id, user in self.users_by_id.items()
            if user.password
        }
        payload["users_by_id"] = users
        payload["users_by_email"] = {
            email: user for email, user in self.users_by_email.items() if user.password
        }
        return payload

    def __setstate__(self, payload: dict[str, object]) -> None:
        self.__dict__.update(payload)
        self._lock = threading.Lock()
        if not hasattr(self, "claim_actors") or not isinstance(self.claim_actors, dict):
            self.claim_actors = {}
        # Drop any legacy stub rows that landed in an older Blob pickle.
        for user_id, user in list(self.users_by_id.items()):
            if user.password:
                continue
            self.users_by_id.pop(user_id, None)
            mapped = self.users_by_email.get(user.email)
            if mapped is user or (mapped is not None and not mapped.password):
                self.users_by_email.pop(user.email, None)
        self._bind_tools()

    def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        nit: str | None,
    ) -> tuple[int, dict[str, object]]:
        with self._lock:
            return self._register(email=email, password=password, full_name=full_name, nit=nit)

    def verify(self, token: str) -> dict[str, object]:
        with self._lock:
            for user in self.users_by_id.values():
                if user.verify_token and same_secret(user.verify_token, token):
                    user.email_verified = True
                    user.verify_token = None
                    return {"user_id": user.id, "email_verified": True}
            raise SimError("token_invalid")

    def login(self, email: str, password: str) -> dict[str, object]:
        with self._lock:
            user = self.users_by_email.get(email.strip().lower())
            if user is None or not same_secret(user.password, password):
                raise SimError("invalid_credentials")
            if not user.email_verified:
                raise SimError("email_not_verified")
            if user.status != "active":
                raise SimError("account_suspended")
            access = issue_access_token(user)
            refresh = "simr_" + secrets.token_urlsafe(24)
            self.sessions[access] = user.id
            return {
                "access_token": access,
                "refresh_token": refresh,
                "user": _user_out(user),
            }

    def user_id_for_token(self, token: str) -> str:
        with self._lock:
            user_id = self.sessions.get(token)
            claims: dict[str, object] = {}
            durable = user_id is not None and user_id in self.users_by_id
            if not durable:
                parsed = parse_access_token(token)
                if parsed is None and user_id is None:
                    raise SimError("token_invalid")
                if parsed is not None:
                    user_id, claims = parsed
            if user_id is None:
                raise SimError("token_invalid")
            if user_id not in self.users_by_id and user_id not in self.claim_actors and claims:
                # Blob miss: keep claim actor out of durable indexes so saves
                # cannot publish password="" over the seeded gate user.
                email = claims.get("email")
                role = claims.get("role")
                status = claims.get("status")
                full_name = claims.get("full_name")
                if (
                    isinstance(email, str)
                    and isinstance(role, str)
                    and isinstance(status, str)
                    and isinstance(full_name, str)
                ):
                    normalized = email.strip().lower()
                    existing = self.users_by_email.get(normalized)
                    if existing is not None and existing.password:
                        user_id = existing.id
                    else:
                        self.claim_actors[user_id] = User(
                            id=user_id,
                            email=normalized,
                            password="",
                            full_name=full_name,
                            role=role,
                            status=status,
                            email_verified=True,
                            nit=None,
                            created_at=iso(utcnow()),
                            verify_token=None,
                        )
            self._active_user(user_id)
            return user_id

    def plans(self) -> dict[str, object]:
        ordered = sorted(PLANS, key=lambda plan: str(plan["id"]))
        return {"plans": ordered, "next_cursor": None}

    def subscribe(self, user_id: str, plan_id: str) -> dict[str, object]:
        with self._lock:
            user = self._active_user(user_id)
            plan = PLANS_BY_ID.get(plan_id)
            if plan is None:
                raise SimError("plan_required")
            existing = self.subs.get(user.id)
            if existing is not None and existing.plan_id == plan_id and existing.status == "active":
                return {
                    "subscription": _sub_out(existing),
                    "invoice": existing.invoice,
                    "payment": existing.payment,
                }
            return self._new_subscription(user, plan)

    def list_subscriptions(self, user_id: str) -> dict[str, object]:
        with self._lock:
            self._active_user(user_id)
            row = self.subs.get(user_id)
            rows = [_sub_out(row)] if row is not None else []
            return {"subscriptions": rows, "next_cursor": None}

    def me(self, user_id: str) -> dict[str, object]:
        with self._lock:
            user = self._active_user(user_id)
            row = self.subs.get(user_id)
            count = self._pond_count(user_id)
            return {
                "user": _user_out(user),
                "subscription": None if row is None else _sub_out(row),
                "ponds_count": count,
            }

    def create_pond(self, user_id: str, name: str, engine: str) -> dict[str, object]:
        with self._lock:
            self._prepare_create(user_id, name)
            return self._insert_pond(user_id, name, engine)

    def list_ponds(self, user_id: str) -> dict[str, object]:
        with self._lock:
            self._active_user(user_id)
            rows = [
                _pond_out(pond)
                for pond in self.ponds.values()
                if pond.user_id == user_id and pond.desired_state != "deleted"
            ]
            return {"ponds": rows, "next_cursor": None}

    def get_pond(self, user_id: str, pond_id: str) -> dict[str, object]:
        with self._lock:
            return {"pond": _pond_out(self._owned_pond(user_id, pond_id))}

    def connection(self, user_id: str, pond_id: str) -> dict[str, object]:
        with self._lock:
            return self._connection(self._owned_pond(user_id, pond_id))

    def apply_pond(self, user_id: str, pond_id: str, command: str) -> dict[str, object]:
        """Sim-only start and stop. Not part of the frozen OpenAPI."""
        with self._lock:
            pond = self._owned_pond(user_id, pond_id)
            desired, observed, healthy = POND_APPLY[command]
            pond.desired_state = desired
            pond.observed_state = observed
            pond.healthy = healthy
            pond.last_error = None
            return {"pond": _pond_out(pond)}

    def trigger_backup(self, user_id: str, pond_id: str) -> dict[str, object]:
        with self._lock:
            pond = self._owned_pond(user_id, pond_id)
            row = self._add_backup(pond, "on_demand")
            return {"backup": _backup_out(row), "job": _job("backup_pond", pond.id)}

    def list_backups(self, user_id: str, pond_id: str) -> dict[str, object]:
        with self._lock:
            pond = self._owned_pond(user_id, pond_id)
            rows = [_backup_out(row) for row in self.backups.get(pond.id, [])]
            return {"backups": rows, "next_cursor": None}

    def run_sql(self, user_id: str, pond_id: str, query: str, mode: str) -> dict[str, object]:
        with self._lock:
            self._owned_pond(user_id, pond_id)
            result = self._execute_sql(query, mode)
            self._record_sql(user_id, pond_id, query, mode, result)
            return result

    def list_sql_history(self, user_id: str, pond_id: str) -> dict[str, object]:
        with self._lock:
            self._owned_pond(user_id, pond_id)
            events = list(self.sql_events.get(pond_id, []))
            return {"events": events, "next_cursor": None}

    def list_admin_ponds(self, actor_id: str) -> dict[str, object]:
        with self._lock:
            self._require_admin(actor_id)
            rows = [
                self._admin_pond_out(pond)
                for pond in sorted(self.ponds.values(), key=lambda row: row.created_at)
                if pond.desired_state != "deleted"
            ]
            return {"ponds": rows, "next_cursor": None}

    def delete_pond(self, user_id: str, pond_id: str) -> dict[str, object]:
        # Preview delete always proposes. POST /confirm/{token} runs it.
        with self._lock:
            pond = self._owned_pond(user_id, pond_id)
            summary = (
                f"Se eliminará el pond '{pond.name}'. "
                "Se creará un respaldo previo automático. Expira en 5 min."
            )
            return self._hold(user_id, "delete_pond", {"pond_id": pond.id}, summary)

    def confirm(
        self,
        user_id: str,
        token: str,
        *,
        expect: str | None = None,
    ) -> tuple[str, dict[str, object]]:
        with self._lock:
            pending = self._peek(user_id, token)
            if expect is not None and pending.action != expect:
                raise SimError("confirmation_action_mismatch")
            body = self._run_pending(user_id, pending)
            pending.consumed = True
            return pending.action, body

    def cancel(self, user_id: str, token: str) -> None:
        with self._lock:
            pending = self._peek(user_id, token)
            pending.consumed = True

    def list_admin_users(self, actor_id: str) -> dict[str, object]:
        with self._lock:
            self._require_admin(actor_id)
            rows = [
                self._admin_out(user)
                for user in sorted(self.users_by_id.values(), key=lambda row: row.created_at)
            ]
            return {"users": rows, "next_cursor": None}

    def usage(self, user_id: str, month: str | None) -> dict[str, object]:
        with self._lock:
            self._active_user(user_id)
            label = month if month else utcnow().strftime("%Y-%m")
            rows: list[dict[str, object]] = []
            total_instance = 0.0
            total_storage = 0.0
            for pond in self.ponds.values():
                if pond.user_id != user_id or pond.desired_state == "deleted":
                    continue
                instance_hours = 1.0 if pond.observed_state == "running" else 0.0
                storage = 0.5
                total_instance += instance_hours
                total_storage += storage
                rows.append(
                    {
                        "pond_id": pond.id,
                        "pond_name": pond.name,
                        "instance_hours": instance_hours,
                        "storage_gb_hours": storage,
                    }
                )
            return {
                "month": label,
                "ponds": rows,
                "total_instance_hours": total_instance,
                "total_storage_gb_hours": total_storage,
            }

    def suspend(self, actor_id: str, target_id: str, confirm_text: str) -> dict[str, object]:
        with self._lock:
            self._require_admin(actor_id)
            if confirm_text != "SUSPENDER":
                raise SimError("confirmation_action_mismatch")
            target = self._any_user(target_id)
            target.status = "suspended"
            return {"user": self._admin_out(target)}

    def reactivate(self, actor_id: str, target_id: str) -> dict[str, object]:
        with self._lock:
            self._require_admin(actor_id)
            target = self._any_user(target_id)
            target.status = "active"
            return {"user": self._admin_out(target)}

    def agent_get(self, user_id: str, base_url: str) -> dict[str, object]:
        with self._lock:
            self._active_user(user_id)
            agent = self._ensure_agent(user_id)
            return self._agent_public(agent, base_url)

    def agent_rotate(self, user_id: str, base_url: str) -> dict[str, object]:
        with self._lock:
            self._active_user(user_id)
            agent = self._ensure_agent(user_id)
            agent.password = secrets.token_urlsafe(18)
            agent.rotated_at = iso(utcnow())
            agent.expires_at = iso(utcnow() + MCP_TTL)
            return {
                "slug": agent.slug,
                "url": base_url.rstrip("/") + "/mcp",
                "password": agent.password,
                "expires_at": agent.expires_at,
            }

    def agent_toggle(self, user_id: str, enabled: bool) -> dict[str, object]:
        with self._lock:
            self._active_user(user_id)
            agent = self._ensure_agent(user_id)
            agent.enabled = enabled
            return {"enabled": agent.enabled}

    def mcp_user(self, slug: str, password: str) -> str:
        with self._lock:
            agent = self.agents_by_slug.get(slug)
            if agent is None or not same_secret(agent.password, password):
                raise SimError("agent_bad_credentials")
            if not agent.enabled:
                raise SimError("agent_disabled")
            if parse_iso(agent.expires_at) <= utcnow():
                raise SimError("agent_bad_credentials")
            user = self.users_by_id.get(agent.user_id)
            if user is None or user.status != "active":
                raise SimError("agent_disabled")
            return agent.user_id

    def mcp_info(self) -> dict[str, object]:
        return {
            "enabled": True,
            "endpoint": "/mcp",
            "read_only_tools": list(READ_ONLY_TOOLS),
            "mutable_tools": list(MUTABLE_TOOLS),
            "prompt_summary": PROMPT_SUMMARY,
        }

    def tool_catalog(self) -> dict[str, object]:
        tools: list[dict[str, object]] = []
        for name in READ_ONLY_TOOLS + MUTABLE_TOOLS:
            tools.append(
                {
                    "name": name,
                    "description": _TOOL_TEXT[name],
                    "inputSchema": _TOOL_SCHEMA[name],
                }
            )
        return {"tools": tools}

    def mcp_call(self, user_id: str, name: str, args: dict[str, object]) -> dict[str, object]:
        with self._lock:
            fn = self._tools.get(name)
            if fn is None:
                raise ToolMiss(name)
            return fn(user_id, args)

    def _register(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        nit: str | None,
    ) -> tuple[int, dict[str, object]]:
        normalized = email.strip().lower()
        if "@" not in normalized or not full_name.strip():
            raise SimError("token_invalid", message="Solicitud inválida")
        if len(password) < 8:
            raise SimError("password_too_weak")
        existing = self.users_by_email.get(normalized)
        if existing is not None:
            # Preview/hosted sim: CI may re-seed gate users with a fresh password
            # against durable Blob state. Never enable this path in production.
            allow_reseed = (
                os.environ.get("VERCEL_ENV", "").strip() == "preview"
                or os.environ.get("KOI_SIM_ALLOW_RESEED", "").strip() == "1"
            )
            if (
                allow_reseed
                and normalized in {GATE_ADMIN_EMAIL, GATE_USER_EMAIL}
                and not same_secret(existing.password, password)
            ):
                existing.password = password
                existing.full_name = full_name.strip() or existing.full_name
                existing.status = "active"
                existing.email_verified = True
                existing.verify_token = None
                return 200, self._register_body(existing)
            if not same_secret(existing.password, password):
                raise SimError("email_taken")
            if not existing.email_verified:
                existing.verify_token = secrets.token_urlsafe(18)
            return 200, self._register_body(existing)
        # Gate emails used by hosted preview CI: skip the verify round-trip so a
        # cold second instance cannot 401 token_invalid before Blob catches up.
        gate = normalized in {GATE_ADMIN_EMAIL, GATE_USER_EMAIL}
        user = User(
            id=str(uuid.uuid4()),
            email=normalized,
            password=password,
            full_name=full_name.strip(),
            role="admin" if normalized == GATE_ADMIN_EMAIL else "client",
            status="active",
            email_verified=gate,
            nit=nit,
            created_at=iso(utcnow()),
            verify_token=None if gate else secrets.token_urlsafe(18),
        )
        self.users_by_email[normalized] = user
        self.users_by_id[user.id] = user
        return 201, self._register_body(user)

    def _register_body(self, user: User) -> dict[str, object]:
        body: dict[str, object] = {
            "user_id": user.id,
            "email_verified": user.email_verified,
        }
        if user.verify_token and not user.email_verified:
            body["verify_token"] = user.verify_token
        return body

    def _active_user(self, user_id: str) -> User:
        user = self.users_by_id.get(user_id) or self.claim_actors.get(user_id)
        if user is None:
            raise SimError("token_invalid")
        if user.status != "active":
            raise SimError("account_suspended")
        if not user.email_verified:
            raise SimError("email_not_verified")
        return user

    def _any_user(self, user_id: str) -> User:
        user = self.users_by_id.get(user_id)
        if user is None:
            raise SimError("not_owner", status=404, message="No existe ese usuario")
        return user

    def _require_admin(self, user_id: str) -> User:
        user = self._active_user(user_id)
        if user.role != "admin":
            raise SimError("admin_only")
        return user

    def _admin_out(self, user: User) -> dict[str, object]:
        sub = self.subs.get(user.id)
        plan = sub.plan_id if sub is not None and sub.status == "active" else None
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "status": user.status,
            "email_verified": user.email_verified,
            "created_at": user.created_at,
            "active_subscription_plan": plan,
        }

    def _admin_pond_out(self, pond: Pond) -> dict[str, object]:
        owner = self.users_by_id.get(pond.user_id)
        return {
            "id": pond.id,
            "owner_email": owner.email if owner is not None else "",
            "name": pond.name,
            "plan_id": pond.plan_id,
            "node_id": NODE_ID,
            "desired_state": pond.desired_state,
            "observed_state": pond.observed_state,
            "host_port": pond.host_port,
            "created_at": pond.created_at,
        }

    def _record_sql(
        self,
        user_id: str,
        pond_id: str,
        query: str,
        mode: str,
        result: dict[str, object],
    ) -> None:
        normalized = mode.strip().lower() if mode else "read"
        if normalized not in {"read", "write"}:
            normalized = "read"
        truncated = query if len(query) <= 4000 else query[:4000]
        row_count = result.get("row_count")
        duration = result.get("duration_ms")
        event = {
            "id": str(uuid.uuid4()),
            "pond_id": pond_id,
            "query_truncated": truncated,
            "mode": normalized,
            "row_count": row_count if isinstance(row_count, int) else 0,
            "duration_ms": duration if isinstance(duration, int) else 0,
            "executed_at": iso(utcnow()),
        }
        bucket = self.sql_events.setdefault(pond_id, [])
        bucket.insert(0, event)
        del bucket[50:]
        _ = user_id  # actor-scoped in production; sim keeps pond-scoped stub.

    def _new_subscription(self, user: User, plan: dict[str, object]) -> dict[str, object]:
        self._invoice_n += 1
        start = utcnow()
        minutes = int(plan["validity_minutes"])
        end = start + timedelta(minutes=minutes)
        price = float(plan["price_monthly_usd"])
        iva = round(price * 0.12, 2)
        total = round(price + iva, 2)
        sub_id = str(uuid.uuid4())
        invoice_id = str(uuid.uuid4())
        number = f"KOI-SIM-{self._invoice_n:04d}"
        invoice: dict[str, object] = {
            "id": invoice_id,
            "number": number,
            "user_id": user.id,
            "subscription_id": sub_id,
            "subtotal_usd": price,
            "iva_usd": iva,
            "total_usd": total,
            "status": "paid",
            "issued_at": iso(start),
            "pdf_path": None,
        }
        payment: dict[str, object] = {
            "id": str(uuid.uuid4()),
            "invoice_id": invoice_id,
            "amount_usd": total,
            "status": "succeeded",
            "method": "simulated",
            "processed_at": iso(start),
        }
        row = Subscription(
            id=sub_id,
            user_id=user.id,
            plan_id=str(plan["id"]),
            status="active",
            current_period_start=iso(start),
            current_period_end=iso(end),
            cancel_at_period_end=False,
            invoice=invoice,
            payment=payment,
        )
        self.subs[user.id] = row
        return {"subscription": _sub_out(row), "invoice": invoice, "payment": payment}

    def _prepare_create(self, user_id: str, name: str) -> None:
        self._active_user(user_id)
        if not name.strip():
            raise SimError("token_invalid", message="El nombre del pond es obligatorio")
        sub = self.subs.get(user_id)
        if sub is None or sub.status != "active":
            raise SimError("plan_required")
        for pond in self.ponds.values():
            if (
                pond.user_id == user_id
                and pond.name == name
                and pond.desired_state != "deleted"
            ):
                raise SimError("pond_name_taken")
        plan = PLANS_BY_ID[sub.plan_id]
        if self._pond_count(user_id) >= int(plan["max_ponds"]):
            raise SimError("quota_exceeded")

    def _pond_count(self, user_id: str) -> int:
        return sum(
            1
            for pond in self.ponds.values()
            if pond.user_id == user_id and pond.desired_state != "deleted"
        )

    def _insert_pond(self, user_id: str, name: str, engine: str) -> dict[str, object]:
        sub = self.subs[user_id]
        if self._next_port > PORT_END:
            raise SimError("node_unavailable")
        port = self._next_port
        self._next_port += 1
        pond = Pond(
            id=str(uuid.uuid4()),
            user_id=user_id,
            plan_id=sub.plan_id,
            name=name,
            engine_version=engine or "16",
            desired_state="running",
            observed_state="provisioning",
            host_port=port,
            healthy=False,
            created_at=iso(utcnow()),
            db_password=secrets.token_urlsafe(12),
        )
        desired, observed, healthy = POND_APPLY["start"]
        pond.desired_state = desired
        pond.observed_state = observed
        pond.healthy = healthy
        self.ponds[pond.id] = pond
        self.backups.setdefault(pond.id, [])
        return {"pond": _pond_out(pond), "job": _job("create_pond", pond.id)}

    def _owned_pond(self, user_id: str, pond_id: str) -> Pond:
        self._active_user(user_id)
        pond = self.ponds.get(pond_id)
        if pond is None or pond.user_id != user_id or pond.desired_state == "deleted":
            raise SimError("pond_not_found")
        return pond

    def _owned_by_name(self, user_id: str, name: str) -> Pond:
        self._active_user(user_id)
        for pond in self.ponds.values():
            if pond.user_id == user_id and pond.name == name and pond.desired_state != "deleted":
                return pond
        raise SimError("pond_not_found")

    def _connection(self, pond: Pond) -> dict[str, object]:
        username = "koi"
        database = pond.name.replace("-", "_")
        password = pond.db_password
        uri = (
            f"postgresql://{quote(username, safe='')}:{quote(password, safe='')}"
            f"@127.0.0.1:{pond.host_port}/{quote(database, safe='')}"
        )
        return {
            "connection": {
                "host": "127.0.0.1",
                "port": pond.host_port,
                "database": database,
                "username": username,
                "password": password,
                "uri": uri,
            }
        }

    def _add_backup(self, pond: Pond, kind: str) -> Backup:
        backup_id = str(uuid.uuid4())
        moment = iso(utcnow())
        row = Backup(
            id=backup_id,
            pond_id=pond.id,
            kind=kind,
            status="succeeded",
            storage_path=f"/var/lib/koicloud/backups/{pond.name}/{backup_id}.dump",
            size_bytes=128,
            sha256=hashlib.sha256(backup_id.encode()).hexdigest(),
            created_at=moment,
            completed_at=moment,
        )
        self.backups.setdefault(pond.id, []).append(row)
        return row

    def _execute_sql(self, query: str, mode: str) -> dict[str, object]:
        write = _sql_is_write(query)
        normalized = mode.strip().lower() if mode else "read"
        if normalized not in {"read", "write"}:
            raise SimError("token_invalid", message="Modo SQL inválido")
        if normalized == "read" and write:
            raise SimError("sql_readonly_violation")
        return _sql_result(query, write=normalized == "write")

    def _hold(
        self,
        user_id: str,
        action: str,
        payload: dict[str, str],
        summary: str,
    ) -> dict[str, object]:
        token = "conf_" + secrets.token_urlsafe(12)
        expires = iso(utcnow() + CONFIRM_TTL)
        self.pending[token] = Pending(
            token=token,
            user_id=user_id,
            action=action,
            payload=payload,
            summary=summary,
            expires_at=expires,
        )
        return {
            "status": "confirmation_required",
            "token": token,
            "summary": summary,
            "expires_at": expires,
            "next": {
                "confirm_url": f"/api/v1/confirm/{token}",
                "cli_example": f"koicloud confirm {token}",
            },
        }

    def _peek(self, user_id: str, token: str) -> Pending:
        pending = self.pending.get(token)
        if pending is None or pending.user_id != user_id or pending.consumed:
            raise SimError("confirmation_not_found")
        if parse_iso(pending.expires_at) <= utcnow():
            raise SimError("confirmation_expired")
        return pending

    def _run_pending(self, user_id: str, pending: Pending) -> dict[str, object]:
        action = pending.action
        payload = pending.payload
        if action == "delete_pond":
            pond = self._owned_pond(user_id, payload["pond_id"])
            self._add_backup(pond, "pre_delete")
            desired, observed, healthy = POND_APPLY["delete"]
            pond.desired_state = desired
            pond.observed_state = observed
            pond.healthy = healthy
            return {
                "pond": _pond_out(pond),
                "jobs": [
                    _job("backup_pond", pond.id),
                    _job("delete_pond", pond.id),
                ],
            }
        if action == "create_pond":
            name = payload["name"]
            engine = payload.get("engine_version", "16")
            self._prepare_create(user_id, name)
            return self._insert_pond(user_id, name, engine)
        if action == "restore_backup":
            pond = self._owned_pond(user_id, payload["pond_id"])
            backup_id = payload["backup_id"]
            found = any(row.id == backup_id for row in self.backups.get(pond.id, []))
            if not found:
                raise SimError("backup_not_found")
            pond.last_restore_at = iso(utcnow())
            desired, observed, healthy = POND_APPLY["start"]
            pond.desired_state = desired
            pond.observed_state = observed
            pond.healthy = healthy
            return {"job": _job("restore_pond", pond.id)}
        if action == "run_sql":
            pond_id = payload["pond_id"]
            self._owned_pond(user_id, pond_id)
            query = payload["query"]
            mode = payload.get("mode", "write")
            result = self._execute_sql(query, mode)
            self._record_sql(user_id, pond_id, query, mode, result)
            return result
        raise SimError("confirmation_not_found")

    def _ensure_agent(self, user_id: str) -> Agent:
        existing = self.agents_by_user.get(user_id)
        if existing is not None:
            return existing
        user = self.users_by_id[user_id]
        slug = "gate-user" if user.email == GATE_USER_EMAIL else "u" + user.id.replace("-", "")[:8]
        if slug in self.agents_by_slug:
            slug = slug + "-" + secrets.token_hex(2)
        moment = iso(utcnow())
        agent = Agent(
            user_id=user_id,
            slug=slug,
            password=secrets.token_urlsafe(18),
            enabled=True,
            rotated_at=moment,
            expires_at=iso(utcnow() + MCP_TTL),
        )
        self.agents_by_user[user_id] = agent
        self.agents_by_slug[slug] = agent
        return agent

    def _agent_public(self, agent: Agent, base_url: str) -> dict[str, object]:
        return {
            "slug": agent.slug,
            "url": base_url.rstrip("/") + "/mcp",
            "enabled": agent.enabled,
            "rotated_at": agent.rotated_at,
            "expires_at": agent.expires_at,
        }

    def _need(self, args: dict[str, object], key: str) -> str:
        value = args.get(key)
        if not isinstance(value, str) or not value.strip():
            raise SimError("invalid_params", message=f"Falta el argumento '{key}'")
        return value

    def _tool_whoami(self, user_id: str, _args: dict[str, object]) -> dict[str, object]:
        user = self._active_user(user_id)
        return {"user_id": user.id, "email": user.email, "role": user.role}

    def _tool_list_ponds(self, user_id: str, _args: dict[str, object]) -> dict[str, object]:
        self._active_user(user_id)
        rows = [
            _pond_out(pond)
            for pond in self.ponds.values()
            if pond.user_id == user_id and pond.desired_state != "deleted"
        ]
        return {"ponds": rows, "next_cursor": None}

    def _tool_get_pond(self, user_id: str, args: dict[str, object]) -> dict[str, object]:
        pond = self._owned_by_name(user_id, self._need(args, "name"))
        return {"pond": _pond_out(pond)}

    def _tool_get_connection(self, user_id: str, args: dict[str, object]) -> dict[str, object]:
        pond = self._owned_by_name(user_id, self._need(args, "name"))
        return self._connection(pond)

    def _tool_list_subscriptions(self, user_id: str, _args: dict[str, object]) -> dict[str, object]:
        self._active_user(user_id)
        row = self.subs.get(user_id)
        rows = [_sub_out(row)] if row is not None else []
        return {"subscriptions": rows, "next_cursor": None}

    def _tool_list_backups(self, user_id: str, args: dict[str, object]) -> dict[str, object]:
        pond = self._owned_by_name(user_id, self._need(args, "pond_name"))
        rows = [_backup_out(row) for row in self.backups.get(pond.id, [])]
        return {"backups": rows, "next_cursor": None}

    def _tool_create_pond(self, user_id: str, args: dict[str, object]) -> dict[str, object]:
        name = self._need(args, "name")
        engine = args.get("engine_version")
        engine_version = engine if isinstance(engine, str) and engine else "16"
        self._prepare_create(user_id, name)
        summary = f"Se creará el pond '{name}'. Expira en 5 min."
        return self._hold(
            user_id,
            "create_pond",
            {"name": name, "engine_version": engine_version},
            summary,
        )

    def _tool_delete_pond(self, user_id: str, args: dict[str, object]) -> dict[str, object]:
        pond = self._owned_by_name(user_id, self._need(args, "name"))
        summary = (
            f"Se eliminará el pond '{pond.name}'. "
            "Se creará un respaldo previo automático. Expira en 5 min."
        )
        return self._hold(user_id, "delete_pond", {"pond_id": pond.id}, summary)

    def _tool_restore(self, user_id: str, args: dict[str, object]) -> dict[str, object]:
        pond = self._owned_by_name(user_id, self._need(args, "pond_name"))
        backup_id = self._need(args, "backup_id")
        found = any(row.id == backup_id for row in self.backups.get(pond.id, []))
        if not found:
            raise SimError("backup_not_found")
        summary = (
            f"Se restaurará el pond '{pond.name}' desde el respaldo {backup_id}. "
            "Expira en 5 min."
        )
        return self._hold(
            user_id,
            "restore_backup",
            {"pond_id": pond.id, "backup_id": backup_id},
            summary,
        )

    def _tool_run_sql(self, user_id: str, args: dict[str, object]) -> dict[str, object]:
        pond = self._owned_by_name(user_id, self._need(args, "pond_name"))
        query = self._need(args, "query")
        mode_raw = args.get("mode")
        mode = mode_raw if isinstance(mode_raw, str) and mode_raw else "read"
        if mode.strip().lower() == "write":
            summary = (
                f"Se ejecutará SQL de escritura en el pond '{pond.name}'. Expira en 5 min."
            )
            return self._hold(
                user_id,
                "run_sql",
                {"pond_id": pond.id, "query": query, "mode": "write"},
                summary,
            )
        result = self._execute_sql(query, mode)
        self._record_sql(user_id, pond.id, query, mode, result)
        return result

    def _tool_confirm(self, user_id: str, args: dict[str, object]) -> dict[str, object]:
        token = self._need(args, "token")
        pending = self._peek(user_id, token)
        body = self._run_pending(user_id, pending)
        pending.consumed = True
        return body

    def _tool_cancel(self, user_id: str, args: dict[str, object]) -> dict[str, object]:
        token = self._need(args, "token")
        pending = self._peek(user_id, token)
        pending.consumed = True
        return {"status": "discarded"}


_OBJECT = {"type": "object", "properties": {}, "additionalProperties": False}


def _schema(properties: dict[str, object], required: list[str]) -> dict[str, object]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


_STR = {"type": "string"}

_TOOL_TEXT = {
    "whoami": "Return the user that owns this MCP session.",
    "list_ponds": "List ponds for the session user.",
    "get_pond": "Return one pond by name.",
    "get_connection": "Return the connection for a pond.",
    "list_subscriptions": "List subscriptions for the session user.",
    "list_backups": "List backups for a pond.",
    "create_pond": "Propose creation of a pond.",
    "delete_pond": "Propose deletion of a pond.",
    "restore_backup": "Propose restore of a backup.",
    "run_sql": "Run read SQL, or propose write SQL.",
    "confirm_action": "Consume a pending confirmation token.",
    "cancel_confirmation": "Discard a pending confirmation token.",
}

_TOOL_SCHEMA: dict[str, dict[str, object]] = {
    "whoami": _OBJECT,
    "list_ponds": _OBJECT,
    "list_subscriptions": _OBJECT,
    "get_pond": _schema({"name": _STR}, ["name"]),
    "get_connection": _schema({"name": _STR}, ["name"]),
    "list_backups": _schema({"pond_name": _STR}, ["pond_name"]),
    "create_pond": _schema({"name": _STR, "engine_version": _STR}, ["name"]),
    "delete_pond": _schema({"name": _STR}, ["name"]),
    "restore_backup": _schema({"pond_name": _STR, "backup_id": _STR}, ["pond_name", "backup_id"]),
    "run_sql": _schema(
        {"pond_name": _STR, "query": _STR, "mode": _STR},
        ["pond_name", "query"],
    ),
    "confirm_action": _schema({"token": _STR}, ["token"]),
    "cancel_confirmation": _schema({"token": _STR}, ["token"]),
}

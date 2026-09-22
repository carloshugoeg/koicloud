from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    CLIENT = "client"
    ADMIN = "admin"


class UserStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class EmailTokenKind(StrEnum):
    VERIFY_EMAIL = "verify_email"
    RESET_PASSWORD = "reset_password"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    CANCELED = "canceled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"


class InvoiceStatus(StrEnum):
    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"


class PaymentStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PENDING = "pending"


class NodeStatus(StrEnum):
    ALIVE = "alive"
    DRAINING = "draining"
    DEAD = "dead"


class PondDesiredState(StrEnum):
    RUNNING = "running"
    STOPPED = "stopped"
    DELETED = "deleted"


class PondObservedState(StrEnum):
    PENDING = "pending"
    PROVISIONING = "provisioning"
    RUNNING = "running"
    STOPPED = "stopped"
    RESTORING = "restoring"
    DELETING = "deleting"
    DELETED = "deleted"
    FAILED = "failed"


class JobType(StrEnum):
    CREATE_POND = "create_pond"
    START_POND = "start_pond"
    STOP_POND = "stop_pond"
    DELETE_POND = "delete_pond"
    BACKUP_POND = "backup_pond"
    RESTORE_POND = "restore_pond"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    LOST = "lost"


class BackupKind(StrEnum):
    DAILY = "daily"
    ON_DEMAND = "on_demand"
    PRE_DELETE = "pre_delete"


class BackupStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class SQLMode(StrEnum):
    READ = "read"
    WRITE = "write"


class AppSurface(StrEnum):
    WEB = "web"
    CLI = "cli"
    MCP = "mcp"
    INTERNAL = "internal"


class ActorKind(StrEnum):
    USER = "user"
    ADMIN = "admin"
    NODE = "node"
    SYSTEM = "system"
    MCP = "mcp"

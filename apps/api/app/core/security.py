from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings
from app.core.enums import UserRole
from app.core.time import utc_now

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generate_opaque_token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(18)}"


def generate_confirmation_token(action: str) -> str:
    slug = action.replace("_", "-")
    return f"conf-{slug}-{secrets.token_urlsafe(12)}"


def _encode_token(payload: dict[str, Any], ttl: timedelta) -> str:
    settings = get_settings()
    now = utc_now()
    token_payload = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "jti": str(uuid4()),
    }
    return jwt.encode(token_payload, settings.jwt_secret, algorithm="HS256")


def issue_access_token(*, subject: str, email: str, role: UserRole) -> str:
    settings = get_settings()
    return _encode_token(
        {"sub": subject, "email": email, "role": role.value, "token_type": "access"},
        ttl=timedelta(minutes=settings.access_token_ttl_minutes),
    )


def issue_refresh_token(*, subject: str, email: str) -> str:
    settings = get_settings()
    return _encode_token(
        {"sub": subject, "email": email, "token_type": "refresh"},
        ttl=timedelta(days=settings.refresh_ttl_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def token_expiry_from_now(seconds: int) -> datetime:
    return datetime.now(tz=UTC) + timedelta(seconds=seconds)

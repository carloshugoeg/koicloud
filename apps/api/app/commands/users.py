from __future__ import annotations

from app.commands import build_user
from app.core.auth import AuthContext
from app.schemas import MeResponse, SubscriptionOut, UpdateProfileRequest, UserResponse


async def get_me(actor: AuthContext) -> MeResponse:
    user = build_user(email=actor.email, full_name=actor.email.split("@", 1)[0].title(), role=actor.role)
    return MeResponse(user=user, subscription=SubscriptionOut.example(), ponds_count=1)


async def update_profile(actor: AuthContext, payload: UpdateProfileRequest) -> UserResponse:
    current = build_user(
        email=actor.email,
        full_name=payload.full_name or actor.email.split("@", 1)[0].title(),
        role=actor.role,
        nit=payload.nit or "0614-220999-101-3",
    )
    return UserResponse(user=current)

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status

from app.modules.auth.service import AuthService
from app.schemas import (
    ErrorResponse,
    RegisterUserRequest,
    RegisterUserResponse,
    VerifyEmailRequest,
)

router = APIRouter(tags=["auth"])


def _error_responses(*codes: int) -> dict[int, dict[str, Any]]:
    return {code: {"model": ErrorResponse} for code in codes}


@router.post(
    "/auth/register",
    response_model=RegisterUserResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="register_user",
    tags=["auth"],
    responses=_error_responses(409, 422),
)
async def register_user(payload: RegisterUserRequest) -> RegisterUserResponse:
    return await AuthService.register_user(payload)


@router.post(
    "/auth/verify",
    response_model=RegisterUserResponse,
    operation_id="verify_email",
    tags=["auth"],
    responses=_error_responses(401, 404, 410),
)
async def verify_email(payload: VerifyEmailRequest) -> RegisterUserResponse:
    return await AuthService.verify_email(payload)

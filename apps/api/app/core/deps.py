from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, Query

from app.core.config import get_settings
from app.core.enums import AppSurface


@dataclass(frozen=True, slots=True)
class PaginationParams:
    cursor: str | None
    limit: int


def pagination_params(
    cursor: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=100),
) -> PaginationParams:
    settings = get_settings()
    return PaginationParams(cursor=cursor, limit=limit or settings.default_limit)


def get_surface(x_koi_surface: str | None = Header(default=None, alias="X-KOI-Surface")) -> AppSurface:
    if x_koi_surface is None:
        return AppSurface.WEB
    try:
        return AppSurface(x_koi_surface)
    except ValueError:
        return AppSurface.WEB


def get_confirmation_token(
    x_koi_confirm_token: str | None = Header(default=None, alias="X-KOI-Confirm-Token"),
) -> str | None:
    return x_koi_confirm_token

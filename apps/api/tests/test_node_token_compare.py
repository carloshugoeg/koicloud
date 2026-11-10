from __future__ import annotations

import pytest

from app.core.auth import get_node_identity, node_token_matches
from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode


def test_node_token_matches_accepts_exact_value() -> None:
    assert node_token_matches("abc", "abc") is True


def test_node_token_matches_rejects_wrong_value() -> None:
    assert node_token_matches("abc", "abd") is False


def test_node_token_matches_rejects_missing_header() -> None:
    assert node_token_matches(None, "abc") is False


def test_node_token_matches_rejects_length_mismatch() -> None:
    assert node_token_matches("ab", "abc") is False


@pytest.mark.asyncio
async def test_get_node_identity_accepts_configured_token() -> None:
    settings = get_settings()
    ctx = await get_node_identity(x_node_token=settings.node_token)
    assert ctx.node_id == settings.node_id


@pytest.mark.asyncio
async def test_get_node_identity_rejects_wrong_token() -> None:
    with pytest.raises(AppError) as exc:
        await get_node_identity(x_node_token="not-the-node-token")
    assert exc.value.code == ErrorCode.TOKEN_INVALID


@pytest.mark.asyncio
async def test_get_node_identity_rejects_missing_token() -> None:
    with pytest.raises(AppError) as exc:
        await get_node_identity(x_node_token=None)
    assert exc.value.code == ErrorCode.TOKEN_INVALID

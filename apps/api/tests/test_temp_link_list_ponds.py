"""Pond-scoped temp links must discover the pinned pond via whoami + list_ponds.

Claude Code (and similar) call list_ponds after whoami. Denying list_ponds with
agent_disabled leaves the agent unable to pick a pond. Cross-pond access and
lifecycle tools stay denied as before.
"""

from __future__ import annotations

from tests.test_temp_link_scope import _audience_client, _seed_temp_audience


def test_temp_whoami_includes_pinned_pond() -> None:
    pond_a, _pond_b, audience = _seed_temp_audience()
    aud = _audience_client()
    response = aud.post(
        "/mcp",
        headers=audience["basic"],
        json={"jsonrpc": "2.0", "id": 1, "method": "whoami", "params": {}},
    )
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    pond = result.get("pond")
    assert isinstance(pond, dict), result
    assert pond.get("id") == pond_a["id"], result
    assert pond.get("name") == pond_a["name"], result


def test_temp_list_ponds_returns_only_pinned_pond() -> None:
    pond_a, pond_b, audience = _seed_temp_audience()
    aud = _audience_client()
    response = aud.post(
        "/mcp",
        headers=audience["basic"],
        json={"jsonrpc": "2.0", "id": 2, "method": "list_ponds", "params": {}},
    )
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result.get("status") != "error", result
    assert result.get("code") != "agent_disabled", result
    ponds = result.get("ponds") or []
    assert len(ponds) == 1, result
    assert ponds[0]["id"] == pond_a["id"], result
    assert ponds[0]["name"] == pond_a["name"], result
    assert all(item["id"] != pond_b["id"] for item in ponds), result


def test_temp_get_pond_other_still_pond_not_found() -> None:
    _pond_a, pond_b, audience = _seed_temp_audience()
    aud = _audience_client()
    other = aud.post(
        "/mcp",
        headers=audience["basic"],
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "get_pond",
            "params": {"name": pond_b["name"]},
        },
    )
    assert other.status_code == 200, other.text
    result = other.json().get("result") or {}
    assert result.get("status") == "error", result
    assert result.get("code") == "pond_not_found", result


def test_temp_create_pond_still_agent_disabled() -> None:
    _pond_a, _pond_b, audience = _seed_temp_audience()
    aud = _audience_client()
    response = aud.post(
        "/mcp",
        headers=audience["basic"],
        json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "create_pond",
            "params": {"name": "should-not-create"},
        },
    )
    assert response.status_code == 403, response.text
    assert response.json().get("code") == "agent_disabled", response.text

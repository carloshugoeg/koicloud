from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel

from koicloud_cli.config import CliConfig, CliSettings, get_settings, load_config, save_config
from koicloud_cli.errors import NotLoggedInError, build_api_error


class ConfirmationProposal(BaseModel):
    """Canonical confirmation payload for CLI mutations."""

    status: str = "confirmation_required"
    token: str
    summary: str
    expires_at: str | None = None
    next: dict[str, Any] | None = None


class ApiClient:
    """Small httpx wrapper for the KoiCloud control plane."""

    def __init__(
        self,
        *,
        config: CliConfig | None = None,
        settings: CliSettings | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.config = config or load_config(self.settings)
        self._client = httpx.Client(
            base_url=self.config.base_url.rstrip("/") + "/",
            timeout=10.0,
            transport=transport,
            headers={"Accept": "application/json"},
        )

    @property
    def is_logged_in(self) -> bool:
        return bool(self.config.access_token)

    def close(self) -> None:
        self._client.close()

    def require_login(self) -> None:
        if not self.is_logged_in:
            raise NotLoggedInError()

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        needs_auth: bool = True,
    ) -> Any:
        response = self._send(method, path, json=json, needs_auth=needs_auth)
        self._raise_for_error(response)
        return self._decode(response)

    def handle_confirmation(self, response: httpx.Response) -> dict[str, Any] | None:
        if response.status_code != 409:
            return None
        try:
            payload = response.json()
        except ValueError:
            return None
        marker = payload.get("status") or payload.get("code")
        if marker != "confirmation_required":
            return None
        proposal = ConfirmationProposal.model_validate(payload)
        return proposal.model_dump(mode="json", exclude_none=True)

    def resolve_mutation(
        self,
        method: str,
        path: str,
        *,
        payload: Any | None = None,
        yes_token: str | None = None,
    ) -> Any:
        if yes_token:
            return self.confirm(yes_token)

        response = self._send(method, path, json=payload, needs_auth=True)
        confirmation = self.handle_confirmation(response)
        if confirmation is not None:
            return confirmation

        self._raise_for_error(response)
        return self._decode(response)

    def confirm(self, token: str) -> Any:
        return self.request("POST", f"confirm/{token}")

    def discard_confirmation(self, token: str) -> None:
        self.request("DELETE", f"confirm/{token}")

    def _send(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        needs_auth: bool,
        allow_refresh: bool = True,
    ) -> httpx.Response:
        headers = {"X-KOI-Surface": "cli"}
        if needs_auth:
            self.require_login()
            assert self.config.access_token is not None
            headers["Authorization"] = f"Bearer {self.config.access_token}"

        response = self._client.request(method, path.lstrip("/"), json=json, headers=headers)
        if (
            response.status_code == 401
            and needs_auth
            and allow_refresh
            and self.config.refresh_token
            and self._refresh_tokens()
        ):
            return self._send(
                method,
                path,
                json=json,
                needs_auth=needs_auth,
                allow_refresh=False,
            )
        return response

    def _refresh_tokens(self) -> bool:
        refresh_token = self.config.refresh_token
        if not refresh_token:
            return False

        response = self._client.post(
            "auth/refresh",
            headers={"X-KOI-Surface": "cli"},
            json={"refresh_token": refresh_token},
        )
        if response.status_code >= 400:
            return False

        payload = response.json()
        self.config = self.config.model_copy(
            update={
                "access_token": payload.get("access_token"),
                "refresh_token": payload.get("refresh_token", refresh_token),
            }
        )
        save_config(self.config, self.settings)
        return True

    def _raise_for_error(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        try:
            payload = response.json()
        except ValueError:
            payload = response.text or f"HTTP {response.status_code}"
        raise build_api_error(response.status_code, payload)

    @staticmethod
    def _decode(response: httpx.Response) -> Any:
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

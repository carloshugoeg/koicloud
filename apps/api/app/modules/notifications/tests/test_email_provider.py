from __future__ import annotations

import logging
from collections.abc import Callable, Mapping

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.modules.notifications import send

RESEND_URL = "https://api.resend.com/emails"
SENDER = "noreply@koicloud.dev"
RECIPIENT = "usuario@koicloud.dev"
VERIFY_URL = "https://app.koicloud.dev/verify?token=email-provider-test"
API_KEY = "re_test_supersecret_do_not_log"
VERIFY_CONTEXT = {"url": VERIFY_URL, "email": RECIPIENT}


class CapturedPost:
    def __init__(self, url: str, headers: dict[str, str], body: dict[str, object]) -> None:
        self.url = url
        self.headers = headers
        self.body = body


def _set_env(monkeypatch: pytest.MonkeyPatch, name: str, value: str | None) -> None:
    if value is None:
        monkeypatch.delenv(name, raising=False)
        return
    monkeypatch.setenv(name, value)


def _settings(
    monkeypatch: pytest.MonkeyPatch,
    *,
    provider: str | None,
    api_key: str | None,
    email_from: str | None,
) -> Settings:
    _set_env(monkeypatch, "EMAIL_PROVIDER", provider)
    _set_env(monkeypatch, "RESEND_API_KEY", api_key)
    _set_env(monkeypatch, "EMAIL_FROM", email_from)
    get_settings.cache_clear()
    return Settings()


def _reset_gate_if_present() -> None:
    import app.modules.notifications.service as service

    reset = getattr(service, "reset_email_gate_for_tests", None)
    if reset is not None:
        reset()


@pytest.fixture(autouse=True)
def _isolate_email_gate():
    get_settings.cache_clear()
    _reset_gate_if_present()
    yield
    get_settings.cache_clear()
    _reset_gate_if_present()


def _capturing_post(
    calls: list[CapturedPost],
    responder: Callable[[int], httpx.Response],
) -> Callable[..., httpx.Response]:
    def fake_post(
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, object],
        timeout: object,
    ) -> httpx.Response:
        del timeout
        calls.append(
            CapturedPost(
                url=url,
                headers={str(key): str(value) for key, value in headers.items()},
                body={str(key): value for key, value in json.items()},
            )
        )
        return responder(len(calls))

    return fake_post


def _authorization(headers: Mapping[str, str]) -> str:
    folded = {key.lower(): value for key, value in headers.items()}
    auth = folded.get("authorization")
    assert auth is not None
    return auth


def _assert_resend_request(call: CapturedPost, *, api_key: str) -> None:
    assert call.url == RESEND_URL
    assert api_key not in call.url
    assert _authorization(call.headers) == f"Bearer {api_key}"
    assert call.body["from"] == SENDER
    assert call.body["to"] == [RECIPIENT]
    assert call.body["subject"] == "Verificá tu correo"
    html = call.body["html"]
    text = call.body["text"]
    assert isinstance(html, str)
    assert isinstance(text, str)
    assert VERIFY_URL in html
    assert VERIFY_URL in text
    assert RECIPIENT in text
    assert api_key not in str(call.body)


def _assert_secret_absent_from_logs(
    api_key: str,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    exc: BaseException,
) -> None:
    assert any(record.levelno >= logging.ERROR for record in caplog.records)
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert RECIPIENT in logged
    assert "verify_email" in logged
    chunks = [caplog.text, logged, str(exc), repr(exc)]
    for record in caplog.records:
        if record.exc_text:
            chunks.append(record.exc_text)
        if record.args:
            chunks.append(repr(record.args))
    captured = capsys.readouterr()
    chunks.append(captured.out)
    chunks.append(captured.err)
    assert api_key not in "\n".join(chunks)


def _bootstrap(settings: Settings, *, post: Callable[..., httpx.Response] | None = None) -> None:
    from app.modules.notifications.service import bootstrap_email_gate

    if post is None:
        bootstrap_email_gate(settings)
        return
    bootstrap_email_gate(settings, post=post)


def _enter_startup() -> None:
    from app.main import create_app

    get_settings.cache_clear()
    app = create_app()
    with TestClient(app):
        return


@pytest.mark.parametrize(
    ("api_key", "email_from"),
    [
        (None, SENDER),
        (API_KEY, None),
        ("", SENDER),
        (API_KEY, ""),
    ],
    ids=["key-unset", "from-unset", "key-blank", "from-blank"],
)
def test_settings_incomplete_resend_env_is_visible(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str | None,
    email_from: str | None,
) -> None:
    settings = _settings(monkeypatch, provider="resend", api_key=api_key, email_from=email_from)
    assert getattr(settings, "email_provider", None) == "resend"
    assert getattr(settings, "resend_api_key", None) == (api_key or "")
    assert getattr(settings, "email_from", None) == (email_from or "")


def test_settings_default_to_console_when_provider_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, provider=None, api_key=None, email_from=None)
    assert getattr(settings, "email_provider", None) == "console"
    assert getattr(settings, "resend_api_key", None) == ""
    assert getattr(settings, "email_from", None) == ""


def test_settings_reads_console_provider_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(
        monkeypatch,
        provider="console",
        api_key=API_KEY,
        email_from=SENDER,
    )
    assert getattr(settings, "email_provider", None) == "console"
    assert getattr(settings, "resend_api_key", None) == API_KEY
    assert getattr(settings, "email_from", None) == SENDER


def test_parse_email_mode_defaults_to_console(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, provider=None, api_key=None, email_from=None)
    from app.modules.notifications.email_mode import ConsoleMode, parse_email_mode

    mode = parse_email_mode(settings)
    assert isinstance(mode, ConsoleMode)
    assert mode.kind == "console"


def test_parse_email_mode_console_ignores_resend_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(
        monkeypatch,
        provider="console",
        api_key=API_KEY,
        email_from=SENDER,
    )
    from app.modules.notifications.email_mode import ConsoleMode, parse_email_mode

    mode = parse_email_mode(settings)
    assert isinstance(mode, ConsoleMode)
    assert mode.kind == "console"


def test_parse_email_mode_resend_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic import SecretStr

    settings = _settings(monkeypatch, provider="resend", api_key=API_KEY, email_from=SENDER)
    from app.modules.notifications.email_mode import ResendMode, parse_email_mode

    mode = parse_email_mode(settings)
    assert isinstance(mode, ResendMode)
    assert mode.kind == "resend"
    assert mode.from_address == SENDER
    assert isinstance(mode.api_key, SecretStr)
    assert mode.api_key.get_secret_value() == API_KEY
    assert API_KEY not in repr(mode)
    assert API_KEY not in repr(mode.api_key)


@pytest.mark.parametrize(
    ("api_key", "email_from"),
    [
        (None, SENDER),
        (API_KEY, None),
        ("", SENDER),
        (API_KEY, ""),
    ],
    ids=["key-unset", "from-unset", "key-blank", "from-blank"],
)
def test_parse_email_mode_rejects_incomplete_resend(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str | None,
    email_from: str | None,
) -> None:
    settings = _settings(monkeypatch, provider="resend", api_key=api_key, email_from=email_from)
    from app.modules.notifications.email_mode import parse_email_mode
    from app.modules.notifications.errors import EmailConfigurationError

    with pytest.raises(EmailConfigurationError):
        parse_email_mode(settings)


@pytest.mark.parametrize(
    ("api_key", "email_from"),
    [
        (None, SENDER),
        (API_KEY, None),
        ("", SENDER),
        (API_KEY, ""),
    ],
    ids=["key-unset", "from-unset", "key-blank", "from-blank"],
)
def test_bootstrap_rejects_incomplete_resend(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str | None,
    email_from: str | None,
) -> None:
    settings = _settings(monkeypatch, provider="resend", api_key=api_key, email_from=email_from)
    from app.modules.notifications.errors import EmailConfigurationError

    with pytest.raises(EmailConfigurationError):
        _bootstrap(settings)


@pytest.mark.parametrize(
    ("api_key", "email_from"),
    [
        (None, SENDER),
        (API_KEY, None),
        ("", SENDER),
        (API_KEY, ""),
    ],
    ids=["key-unset", "from-unset", "key-blank", "from-blank"],
)
def test_startup_rejects_incomplete_resend(
    monkeypatch: pytest.MonkeyPatch,
    api_key: str | None,
    email_from: str | None,
) -> None:
    _settings(monkeypatch, provider="resend", api_key=api_key, email_from=email_from)
    from app.modules.notifications.errors import EmailConfigurationError

    with pytest.raises(EmailConfigurationError):
        _enter_startup()


def test_send_posts_rendered_message_to_resend(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, provider="resend", api_key=API_KEY, email_from=SENDER)
    calls: list[CapturedPost] = []

    def responder(_attempt: int) -> httpx.Response:
        return httpx.Response(200, json={"id": "msg_123"})

    _bootstrap(settings, post=_capturing_post(calls, responder))
    result = send("verify_email", RECIPIENT, VERIFY_CONTEXT)

    assert len(calls) == 1
    _assert_resend_request(calls[0], api_key=API_KEY)
    assert result.template == "verify_email"
    assert result.to == RECIPIENT
    assert result.subject == "Verificá tu correo"
    assert VERIFY_URL in result.text_body
    assert VERIFY_URL in result.html_body


def test_send_retries_resend_once_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, provider="resend", api_key=API_KEY, email_from=SENDER)
    calls: list[CapturedPost] = []

    def responder(attempt: int) -> httpx.Response:
        if attempt == 1:
            return httpx.Response(503, text="temporary upstream failure")
        return httpx.Response(200, json={"id": "msg_retry"})

    _bootstrap(settings, post=_capturing_post(calls, responder))
    result = send("verify_email", RECIPIENT, VERIFY_CONTEXT)

    assert len(calls) == 2
    assert result.subject == "Verificá tu correo"
    assert result.to == RECIPIENT
    for call in calls:
        _assert_resend_request(call, api_key=API_KEY)


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 422])
def test_send_resend_client_error_fails_without_retry(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
) -> None:
    settings = _settings(monkeypatch, provider="resend", api_key=API_KEY, email_from=SENDER)
    calls: list[CapturedPost] = []

    def responder(_attempt: int) -> httpx.Response:
        return httpx.Response(status_code, text="client error")

    _bootstrap(settings, post=_capturing_post(calls, responder))
    from app.modules.notifications.errors import NotificationDeliveryError

    with pytest.raises(NotificationDeliveryError):
        send("verify_email", RECIPIENT, VERIFY_CONTEXT)

    assert len(calls) == 1
    _assert_resend_request(calls[0], api_key=API_KEY)


def test_send_retries_resend_429_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, provider="resend", api_key=API_KEY, email_from=SENDER)
    calls: list[CapturedPost] = []

    def responder(attempt: int) -> httpx.Response:
        if attempt == 1:
            return httpx.Response(429, text="rate limited")
        return httpx.Response(200, json={"id": "msg_rate_limit"})

    _bootstrap(settings, post=_capturing_post(calls, responder))
    result = send("verify_email", RECIPIENT, VERIFY_CONTEXT)

    assert len(calls) == 2
    assert result.to == RECIPIENT
    for call in calls:
        _assert_resend_request(call, api_key=API_KEY)


def test_send_retries_resend_5xx_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, provider="resend", api_key=API_KEY, email_from=SENDER)
    calls: list[CapturedPost] = []

    def responder(attempt: int) -> httpx.Response:
        if attempt == 1:
            return httpx.Response(500, text="upstream boom")
        return httpx.Response(200, json={"id": "msg_5xx"})

    _bootstrap(settings, post=_capturing_post(calls, responder))
    result = send("verify_email", RECIPIENT, VERIFY_CONTEXT)

    assert len(calls) == 2
    assert result.to == RECIPIENT
    for call in calls:
        _assert_resend_request(call, api_key=API_KEY)


def test_send_retries_resend_transport_error_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(monkeypatch, provider="resend", api_key=API_KEY, email_from=SENDER)
    calls: list[CapturedPost] = []

    def responder(attempt: int) -> httpx.Response:
        if attempt == 1:
            raise httpx.ConnectError("connection refused")
        return httpx.Response(200, json={"id": "msg_transport"})

    _bootstrap(settings, post=_capturing_post(calls, responder))
    result = send("verify_email", RECIPIENT, VERIFY_CONTEXT)

    assert len(calls) == 2
    assert result.to == RECIPIENT
    for call in calls:
        _assert_resend_request(call, api_key=API_KEY)


def test_send_resend_api_error_raises_without_logging_key(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = _settings(monkeypatch, provider="resend", api_key=API_KEY, email_from=SENDER)
    calls: list[CapturedPost] = []

    def responder(_attempt: int) -> httpx.Response:
        return httpx.Response(502, text=f'{{"message":"rejected {API_KEY}"}}')

    _bootstrap(settings, post=_capturing_post(calls, responder))
    from app.modules.notifications.errors import NotificationDeliveryError

    caplog.set_level(logging.DEBUG)
    with pytest.raises(NotificationDeliveryError) as caught:
        send("verify_email", RECIPIENT, VERIFY_CONTEXT)

    assert len(calls) == 2
    for call in calls:
        _assert_resend_request(call, api_key=API_KEY)
    _assert_secret_absent_from_logs(API_KEY, caplog, capsys, caught.value)


def test_send_resend_timeout_raises_without_logging_key(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = _settings(monkeypatch, provider="resend", api_key=API_KEY, email_from=SENDER)
    calls: list[CapturedPost] = []

    def responder(_attempt: int) -> httpx.Response:
        raise httpx.TimeoutException(f"timed out while sending Authorization Bearer {API_KEY}")

    _bootstrap(settings, post=_capturing_post(calls, responder))
    from app.modules.notifications.errors import NotificationDeliveryError

    caplog.set_level(logging.DEBUG)
    with pytest.raises(NotificationDeliveryError) as caught:
        send("verify_email", RECIPIENT, VERIFY_CONTEXT)

    assert len(calls) == 2
    for call in calls:
        _assert_resend_request(call, api_key=API_KEY)
    _assert_secret_absent_from_logs(API_KEY, caplog, capsys, caught.value)


def test_console_gate_prints_message_and_does_not_post(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = _settings(
        monkeypatch,
        provider="console",
        api_key=API_KEY,
        email_from=SENDER,
    )
    calls: list[CapturedPost] = []

    def responder(_attempt: int) -> httpx.Response:
        raise AssertionError("console mode must not POST to Resend")

    _bootstrap(settings, post=_capturing_post(calls, responder))
    result = send("verify_email", RECIPIENT, VERIFY_CONTEXT)
    captured = capsys.readouterr()

    assert calls == []
    assert result.subject == "Verificá tu correo"
    assert result.to == RECIPIENT
    assert VERIFY_URL in captured.out
    assert RECIPIENT in captured.out
    assert "Verificá tu correo" in captured.out
    assert API_KEY not in captured.out


def test_send_without_bootstrap_stays_on_console_even_if_env_is_resend(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _settings(monkeypatch, provider="resend", api_key=None, email_from=None)
    result = send("verify_email", f"  {RECIPIENT}  ", VERIFY_CONTEXT)
    captured = capsys.readouterr()

    assert result.template == "verify_email"
    assert result.to == RECIPIENT
    assert result.subject == "Verificá tu correo"
    assert VERIFY_URL in result.text_body
    assert VERIFY_URL in result.html_body
    assert VERIFY_URL in captured.out
    assert RECIPIENT in captured.out
    assert "Verificá tu correo" in captured.out


def test_reset_email_gate_restores_console_send(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    settings = _settings(monkeypatch, provider="resend", api_key=API_KEY, email_from=SENDER)
    calls: list[CapturedPost] = []

    def responder(_attempt: int) -> httpx.Response:
        return httpx.Response(200, json={"id": "msg_should_not_send"})

    _bootstrap(settings, post=_capturing_post(calls, responder))
    from app.modules.notifications.service import reset_email_gate_for_tests

    reset_email_gate_for_tests()
    result = send("verify_email", RECIPIENT, VERIFY_CONTEXT)
    captured = capsys.readouterr()

    assert calls == []
    assert result.subject == "Verificá tu correo"
    assert "Verificá tu correo" in captured.out

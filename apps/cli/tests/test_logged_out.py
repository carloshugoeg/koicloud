from __future__ import annotations

from koicloud_cli.main import app


def test_logged_out_command_exits_with_login_hint(runner) -> None:
    result = runner.invoke(app, ["pond", "list"])

    assert result.exit_code == 1
    assert "Primero corré `koicloud login`." in result.output

"""What the demo replay prints and which /mcp calls it makes."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "demo-mcp-replay.py"
POND = "inventario-natural"
SUMMARY_CREATE = "Se creará el pond 'inventario-natural'. Expira en 5 min."
SUMMARY_DELETE = "Se eliminará el pond 'inventario-natural'. Expira en 5 min."


class Api:
    def __init__(self) -> None:
        self.pond = None
        self.calls = []
        self.pending = {}
        self.busy_deletes = 0
        self.read_requires_confirmation = False
        self.flip_to_running = True
        self.auth = "Basic " + base64.b64encode(b"demo-agent:koicloud-demo").decode("ascii")
        self.lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    api: Api

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        if self.path.rstrip("/") != "/mcp":
            self._send(404, {"code": "not_found", "message": "not mcp", "request_id": None})
            return
        if self.headers.get("Authorization") != self.api.auth:
            self._send(
                401,
                {"code": "agent_bad_credentials", "message": "bad", "request_id": None},
            )
            return
        try:
            body = json.loads(raw.decode())
        except json.JSONDecodeError:
            self._send(400, {"code": "bad_json", "message": "bad", "request_id": None})
            return
        status, payload = self._dispatch(body)
        self._send(status, payload)

    def _dispatch(self, body: dict) -> tuple[int, dict]:
        if body.get("method") != "tools/call":
            return 400, {"code": "bad_method", "message": "tools/call", "request_id": None}
        params = body.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        with self.api.lock:
            self.api.calls.append({"name": name, "arguments": arguments})
            outcome = self._tool(name, arguments)
        if outcome[0] != 200:
            return outcome
        return 200, {"jsonrpc": "2.0", "id": body.get("id"), "result": outcome[1], "error": None}

    def _tool(self, name: object, arguments: dict) -> tuple[int, dict]:
        if name == "list_ponds":
            if self.api.pond == "pending" and self.api.flip_to_running:
                self.api.pond = "running"
            ponds = []
            if self.api.pond is not None:
                ponds.append({"name": POND, "observed_state": self.api.pond})
            return 200, {"ponds": ponds, "next_cursor": None}
        if name == "create_pond":
            token = self._propose("create_pond", SUMMARY_CREATE)
            return 200, _confirmation(token, SUMMARY_CREATE)
        if name == "delete_pond":
            if self.api.pond is None:
                return 404, {"code": "pond_not_found", "message": "missing", "request_id": None}
            token = self._propose("delete_pond", SUMMARY_DELETE)
            return 200, _confirmation(token, SUMMARY_DELETE)
        if name == "run_sql":
            if self.api.read_requires_confirmation:
                token = self._propose("run_sql", "no debería confirmarse")
                return 200, _confirmation(token, "no debería confirmarse")
            return 200, {
                "columns": ["now"],
                "rows": [["2026-10-21T00:00:00Z"]],
                "row_count": 1,
                "duration_ms": 4,
                "truncated": False,
            }
        if name == "confirm_action":
            return self._confirm(arguments.get("token"))
        return 400, {"code": "unknown_tool", "message": str(name), "request_id": None}

    def _propose(self, action: str, summary: str) -> str:
        token = f"conf-{action}-{len(self.api.pending) + 1}"
        self.api.pending[token] = action
        return token

    def _confirm(self, token: object) -> tuple[int, dict]:
        action = self.api.pending.pop(token, None) if isinstance(token, str) else None
        if action is None:
            return 404, {"code": "confirmation_not_found", "message": "missing", "request_id": None}
        if action == "create_pond":
            self.api.pond = "pending"
            return 200, {
                "pond": {"name": POND, "desired_state": "running"},
                "job": {"type": "create_pond", "status": "queued"},
            }
        if action == "delete_pond":
            if self.api.busy_deletes > 0:
                self.api.busy_deletes -= 1
                return 409, {"code": "pond_busy", "message": "job activo", "request_id": None}
            self.api.pond = None
            return 200, {
                "pond": {"name": POND, "desired_state": "deleted"},
                "jobs": [{"type": "backup", "status": "queued"}],
            }
        return 400, {"code": "confirmation_action_mismatch", "message": action, "request_id": None}

    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _confirmation(token: str, summary: str) -> dict:
    return {
        "status": "confirmation_required",
        "token": token,
        "summary": summary,
        "expires_at": "2026-10-21T00:05:00Z",
        "next": {"confirm_url": f"/api/v1/confirm/{token}", "cli_example": f"koicloud confirm {token}"},
    }


def serve(api: Api) -> tuple[ThreadingHTTPServer, str]:
    handler = type("BoundHandler", (Handler,), {"api": api})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, f"http://{host}:{port}"


def replay(base_url: str, *, wait_s: str = "2") -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "KOICLOUD_API_URL": base_url,
        "KOICLOUD_MCP_SLUG": "demo-agent",
        "KOICLOUD_MCP_PASSWORD": "koicloud-demo",
        "KOICLOUD_REPLAY_POLL_S": "0.01",
        "KOICLOUD_REPLAY_WAIT_S": wait_s,
    }
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--simulate-chat"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def tool_names(api: Api) -> list[str]:
    return [call["name"] for call in api.calls if call["name"] != "list_ponds"]


class ReplayTest(unittest.TestCase):
    def test_chat_follows_the_sealed_sequence_and_can_repeat(self) -> None:
        api = Api()
        server, base = serve(api)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        first = replay(base)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("Tú: dame un pond nuevo llamado inventario-natural", first.stdout)
        self.assertIn(SUMMARY_CREATE, first.stdout)
        self.assertIn("Tú: confírmalo", first.stdout)
        self.assertIn("Tú: corré SELECT now() contra inventario-natural", first.stdout)
        self.assertIn("2026-10-21T00:00:00Z", first.stdout)
        self.assertIn(SUMMARY_DELETE, first.stdout)
        self.assertIn("Tú: eliminá inventario-natural con backup previo", first.stdout)
        self.assertEqual(
            tool_names(api),
            ["create_pond", "confirm_action", "run_sql", "delete_pond", "confirm_action"],
        )
        sql = next(call for call in api.calls if call["name"] == "run_sql")
        self.assertEqual(
            sql["arguments"],
            {"pond_name": POND, "query": "SELECT now()", "mode": "read"},
        )
        create = next(call for call in api.calls if call["name"] == "create_pond")
        self.assertEqual(create["arguments"], {"name": POND})
        self.assertIsNone(api.pond)

        second = replay(base)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(tool_names(api).count("create_pond"), 2)
        self.assertIsNone(api.pond)

    def test_leftover_pond_is_deleted_with_confirmation_before_the_script(self) -> None:
        api = Api()
        api.pond = "running"
        server, base = serve(api)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        result = replay(base)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Lo elimino con confirmación antes de repetir el guion.", result.stdout)
        self.assertEqual(
            tool_names(api),
            [
                "delete_pond",
                "confirm_action",
                "create_pond",
                "confirm_action",
                "run_sql",
                "delete_pond",
                "confirm_action",
            ],
        )
        self.assertIsNone(api.pond)

    def test_pending_job_stops_before_delete_confirm(self) -> None:
        api = Api()
        api.flip_to_running = False
        server, base = serve(api)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        result = replay(base, wait_s="0.2")
        self.assertEqual(result.returncode, 1)
        self.assertIn("pond_busy", result.stderr)
        self.assertIn("Espero a que ese job termine antes de confirmar el borrado.", result.stdout)
        self.assertNotIn("delete_pond", tool_names(api))
        self.assertEqual(api.pond, "pending")

    def test_read_sql_does_not_confirm(self) -> None:
        api = Api()
        api.read_requires_confirmation = True
        server, base = serve(api)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        result = replay(base)
        self.assertEqual(result.returncode, 1)
        self.assertIn("unexpected_confirmation", result.stderr)
        self.assertNotIn("confirm_action", tool_names(api)[2:])
        self.assertNotIn("delete_pond", tool_names(api))

    def test_busy_delete_proposes_again(self) -> None:
        api = Api()
        api.busy_deletes = 1
        server, base = serve(api)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        result = replay(base)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("vuelvo a pedir confirmación", result.stdout)
        self.assertEqual(tool_names(api).count("delete_pond"), 2)
        self.assertIsNone(api.pond)


if __name__ == "__main__":
    unittest.main()

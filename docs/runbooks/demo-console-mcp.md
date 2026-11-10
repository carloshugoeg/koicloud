# Demo S3: link temporal en agentes de consola

Cómo pegar el link + password de acceso temporal (S2 / issue #203) en Claude Code,
Cursor CLI o Codex CLI para llamar tools MCP del pond fijado.

ChatGPT web y claude.ai web quedan fuera de este runbook (issue #204).

## Prerrequisito

1. Un pond `running` del presentador.
2. `POST /api/v1/ponds/{pond_id}/temp-access` devolvió `url`, `slug` y `password` (una sola vez).
3. Tools permitidas en esta base: `whoami`, `get_pond`, `run_sql`. No uses `list_tables`
   hasta que aterrice S5 (#206).

Sustituí `URL`, `SLUG` y `PASSWORD` por los valores del create. El Authorization es
`Basic base64(SLUG:PASSWORD)`.

## Claude Code

```bash
claude mcp add koicloud --transport http URL --header "Authorization: Basic <base64(SLUG:PASSWORD)>"
```

Comprobá con el agente: pedile `whoami` y luego el detalle del pond por nombre.

## Cursor CLI

Pegá en `.cursor/mcp.json` (o la config MCP del CLI):

```json
{
  "mcpServers": {
    "koicloud": {
      "url": "URL",
      "headers": {
        "Authorization": "Basic <base64(SLUG:PASSWORD)>"
      }
    }
  }
}
```

## Codex CLI

Pegá en `~/.codex/config.toml` (o `.codex/config.toml` del proyecto):

```toml
[mcp_servers.koicloud]
url = "URL"

[mcp_servers.koicloud.http_headers]
Authorization = "Basic <base64(SLUG:PASSWORD)>"
```

`codex mcp add` aún no persiste headers arbitrarios; editá el TOML a mano.

## Qué debe pasar

1. Auth ok → sesión pond-pinned (`AuthContext.pond_id` fijado).
2. `whoami` o `get_pond` del pond del link responden.
3. Password incorrecto → `401 agent_bad_credentials`.
4. `create_pond` / otro pond → denegado; la sesión sigue pinned.

Diagrama y reglas: `docs/architecture/statecharts/console-mcp-connect/`.

## Generar el snippet desde código

```python
from app.mcp.console_snippets import build_snippet

print(build_snippet("claude_code", url=url, slug=slug, password=password))
print(build_snippet("cursor_cli", url=url, slug=slug, password=password))
print(build_snippet("codex_cli", url=url, slug=slug, password=password))
```

Smoke: `cd apps/api && uv run pytest -q tests/test_console_mcp_snippets.py`.

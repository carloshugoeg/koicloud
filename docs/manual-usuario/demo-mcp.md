# Demo MCP sin LLM (fallback)

Cuando Claude o Cursor no responden en la demo, usá el replay determinista. Reproduce el happy path del plan sellado (`create_pond` → confirm → `run_sql` read → `delete_pond` → confirm) contra `POST /mcp`, sin modelo ni red externa.

## Cómo invocarlo

Con la API y el node-agent en marcha:

```bash
python3 scripts/demo-mcp-replay.py --simulate-chat
```

Variables opcionales: `KOICLOUD_API_URL` (default `http://127.0.0.1:8000`), `KOICLOUD_MCP_SLUG`, `KOICLOUD_MCP_PASSWORD`.

## Salida feliz

Con `--simulate-chat` verás el diálogo `Tú` / `Asistente` para el pond `inventario-natural`, el `summary` del backend sin reescribirlo, un `SELECT now()` en modo read y el borrado con confirmación. Una segunda ejecución limpia residuos y termina igual.

Detalle operativo: `docs/runbooks/demo-mcp-replay.md`. Guion y riesgos: `docs/architecture/risks-and-demo-plan.md` §4.

## Acceso temporal: SQL write sin JWT de dueño

El cliente de audiencia autentica solo con Basic `pond-<slug>:<password>` (sin Bearer del dueño):

1. `run_sql(pond_name, query, mode="write")` → `confirmation_required` con `token` (`next.confirm_url` = `/mcp`).
2. En una segunda llamada, el **mismo** Basic invoca `confirm_action(token)`.
3. Un `run_sql` en modo `read` prueba que la tabla existe.

No uses el JWT del dueño para confirmar esa propuesta. El dueño solo emite o revoca el credential temporal por REST.

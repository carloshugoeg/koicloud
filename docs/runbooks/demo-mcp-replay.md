# Demo MCP replay (fallback sin LLM)

Script: [`scripts/demo-mcp-replay.py`](../../scripts/demo-mcp-replay.py).
Plan sellado: [`../architecture/risks-and-demo-plan.md`](../architecture/risks-and-demo-plan.md) §4.

## Invocación

```bash
# API local tras make up + seed
python3 scripts/demo-mcp-replay.py \
  --base-url http://127.0.0.1:8000 \
  --slug demo-agent \
  --password koicloud-demo \
  --simulate-chat
```

Credenciales demo por defecto: slug `demo-agent`, password `koicloud-demo`
(settings `MCP_DEMO_*` / seed). Contra VPS usá el slug+password del usuario demo.

## Salida feliz

Con `--simulate-chat`, una transcripción `user:` / `assistant:` que recorre:

1. `create_pond` → summary + token  
2. `confirm_action`  
3. `run_sql` read `SELECT now()`  
4. `delete_pond` → summary + token  
5. `confirm_action`  

Termina con `replay OK`. Una segunda ejecución limpia residuos de `inventario-natural` antes de repetir.

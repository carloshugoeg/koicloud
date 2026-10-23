# Correr la demo MCP sin un LLM

El guion sellado está en la sección 4 de `docs/architecture/risks-and-demo-plan.md`. El script llama a `POST /mcp` y usa la misma confirmación que el IDE. No crea ni borra el pond en el paso en que lo propone. No usa LLM ni red externa: solo habla con la API local (o la URL que indiques).

## Correr el guion

La API y el node-agent tienen que estar en marcha. Desde la raíz del repo:

```bash
python3 scripts/demo-mcp-replay.py --simulate-chat
```

Por defecto habla con `http://127.0.0.1:8000`, slug `demo-agent` y contraseña `koicloud-demo`.

Para otro host, exportá las variables y volvé a correr el mismo comando.

```bash
export KOICLOUD_API_URL=https://koicloud.example
export KOICLOUD_MCP_SLUG=el-slug
export KOICLOUD_MCP_PASSWORD=la-contraseña
python3 scripts/demo-mcp-replay.py --simulate-chat
```

## Leer la transcripción

Con `--simulate-chat` vas a ver estas líneas, en este orden.

1. `Tú` pide el pond `inventario-natural`.
2. `Asistente` repite el `summary` que devolvió `create_pond`, sin cambiarlo.
3. `Tú` dice `confírmalo` y el script llama a `confirm_action`.
4. `Tú` pide `SELECT now()` y `run_sql` corre en modo `read`.
5. `Tú` pide borrar el pond. `delete_pond` muestra su `summary` y hace falta otro `confírmalo`.

Si `inventario-natural` ya existe, el script lo borra con `delete_pond` y `confirm_action` antes de repetir el guion. Una segunda corrida termina igual que la primera.

Si el pond sigue en `pending` o en `provisioning`, el script espera. El tope es `KOICLOUD_REPLAY_WAIT_S` (90 s por defecto). Si el node-agent no termina el job, el script corta con `pond_busy` o `pond_not_ready` y no confirma el borrado.

## Prueba sin red externa

```bash
python3 -m unittest scripts.test_demo_mcp_replay -v
```

El stub HTTP local habla streamable MCP; no hay LLM ni salida a Internet. Dos corridas seguidas dejan el mismo stdout cuando el stub arranca limpio.

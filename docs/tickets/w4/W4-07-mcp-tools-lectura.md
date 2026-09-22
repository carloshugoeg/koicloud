---
id: W4-07
workstream: W4
persona: Diego
estado: abierto
rama: w4-mcp-tools-lectura
epica: "E9-02, E5-03, E7-04"
sprint: S4
pr:
---

# [W4-07] Seis tools MCP de **solo lectura**

## Qué se ve

Seis tools FastMCP read-only, cortas y copiando el patrón de referencia de W1. El resultado visible es que `/mcp` expone solo lecturas, sin abrir mutaciones nuevas.

## Entradas ya decididas (no se cambian)

- Ruta propia: `apps/api/app/mcp/**`, pero solo archivos de sus tools de lectura.
- Cada tool debe quedar en 25 líneas o menos y delegar en comandos/servicios ya existentes.
- Candidatas permitidas por contrato: `whoami`, `list_ponds`, `get_pond`, `get_connection`, `list_subscriptions`, `list_backups`, `get_usage`.
- El store no fija cuál de esas 7 queda fuera para llegar a 6 tools.
- No se tocan gate, prompt, server ni tools mutantes.

## Criterios de aceptación

1. Se crean exactamente seis tools read-only y cada archivo queda en 25 líneas o menos.
2. Cada tool devuelve datos con shape del contrato, sin keys extra.
3. Hay pruebas in-process de FastMCP para registro y al menos una llamada.
4. Ninguna tool escribe datos ni bypassea ownership.

## No tocar

- `apps/api/app/mcp/{server.py,gate.py,prompt.py}`.
- Cualquier tool mutante (`create_pond`, `delete_pond`, `restore_backup`, `run_sql` write, `confirm_action`).
- `apps/api/app/commands/**`.
- `apps/node-agent/**`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes comandos, flags, payloads, tools ni atajos al flujo de confirmación.
- Si W1 no elige el subconjunto final de 6, bloqueá y no descartes una tool arbitrariamente.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

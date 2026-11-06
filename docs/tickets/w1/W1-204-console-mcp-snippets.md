---
id: W1-204
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-204-console-mcp-snippets
epica: "E9-02"
sprint: S3
pr: https://github.com/carloshugoeg/koicloud/pull/219

depends_on:
---

# [W1-204] S3 demo: el link temporal funciona pegado en un agente de consola (Claude Code, Cursor CLI, Codex CLI)

## Qué se ve

Un miembro de la audiencia pega el link temporal + password (S2 / #203) en Claude Code,
Cursor CLI o Codex CLI y puede llamar tools MCP permitidas sobre el pond fijado. Hay un
snippet de configuración documentado por cliente y smoke/e2e por cliente que prueba al
menos una tool de lectura (`whoami` o `get_pond`) y que el actor sigue pond-pinned.

## Entradas ya decididas (no se cambian)

- Auth MCP: Basic `slug:password` (o `X-KOI-Agent-Password`) contra `/mcp` (`app/mcp/gate.py`).
- `TEMP_ACCESS_TOOLS` = `whoami` / `get_pond` / `run_sql` (sin `list_tables` en esta base).
- Snippets de cuenta completa en `apps/web/.../agent-access/snippets.ts` son el patrón de
  forma, no se copian a PR #198 ni se mezclan con #205.
- Stack sobre `w1-203-pond-temp-access` (PR #211). Base del PR = esa rama, no `main`.

## Criterios de aceptación

1. Snippet documentado para Claude Code autentica con link+password y llama tools permitidas.
2. Snippet documentado para Cursor CLI autentica igual.
3. Snippet documentado para Codex CLI autentica igual.
4. Smoke/e2e por cliente verifica `whoami` o `get_pond` y que el actor permanece pond-pinned.
5. ChatGPT web y claude.ai web quedan fuera de alcance.

## No tocar

`packages/contracts/**`, OpenAPI, firmas de `commands/*`, migraciones, PR #198, rama
`w1-205-temp-sql-autoconfirm` (#218), conectores web de ChatGPT/claude.ai.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.

## Referencia

Issue #204 · PR #211 (S2 temp-access) · statechart
`docs/architecture/statecharts/console-mcp-connect/`.

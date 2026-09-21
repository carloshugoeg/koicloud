# W4 — Superficies y operación · Diego

Plan de tickets del workstream. Un ticket se trabaja **solo** cuando existe su archivo
`W4-nn-<slug>.md` con `estado: abierto` y las seis secciones. Mientras diga *por escribir*,
no existe todavía. `00-INDEX.md` no es un ticket y el agente lo ignora.

| ID | Título | Rama | Estado |
|---|---|---|---|
| W4-01 | CLI `login`, `logout`, `whoami` | `w4-cli-auth` | por escribir |
| W4-02 | CLI `pond get/create/connection/delete` | `w4-cli-ponds` | por escribir |
| W4-03 | CLI `sql run` (lectura y `--write`) e historial | `w4-cli-sql` | por escribir |
| W4-04 | CLI `subscription`, `backup`, `agent`, `usage` | `w4-cli-resto` | por escribir |
| W4-05 | CLI `confirm` / `confirm cancel` y salida `-o json` | `w4-cli-confirm` | por escribir |
| W4-06 | Módulo `sql_console`: router e historial | `w4-sql-console-router` | por escribir |
| W4-07 | Seis tools MCP de **solo lectura** | `w4-mcp-tools-lectura` | por escribir |
| W4-08 | k6: `login`, `list_ponds`, `create_pond` | `w4-k6` | por escribir |
| W4-09 | `scripts/demo-mcp-replay.py` (repetición determinista) | `w4-demo-replay` | por escribir |
| W4-10 | Manual de usuario (PDF) | `w4-manual-usuario` | por escribir |
| W4-11 | Manual técnico (PDF) | `w4-manual-tecnico` | por escribir |
| W4-12 | Reporte de carga y tres runbooks | `w4-reporte-carga` | por escribir |

**El montaje de `/mcp`, el gate y todas las tools mutantes son de W1.** W4 implementa solo
tools de lectura, copiando las dos de referencia, con ≤ 25 líneas cada una. Es la única
superficie donde un error destruye datos de verdad.

**`propose → confirm` no se optimiza:** una mutación nunca se ejecuta en el mismo turno en
que se propone. Contrato en `docs/architecture/api-surface.md` §6.

**Rutas propias:** `apps/api/app/modules/sql_console/**`, `apps/api/app/mcp/**` (solo los
archivos de sus tools de lectura), `apps/cli/**`, `infra/**`, `load/**`, los manuales y
`.github/workflows/deploy.yml` (con aprobación de W1).

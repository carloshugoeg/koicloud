---
id: W1-26
workstream: W1
persona: Carlos
estado: abierto
rama: w1-demo-replay
epica: "E9-07"
sprint: S4
pr:
depends_on:
---

# [W1-26] `scripts/demo-mcp-replay.py` (repetición determinista)

Antes **W4-09** (Diego). Carlos asumió el ticket: `scripts/**` es zona W1 y la rama debe ser `w1-*` (issue [#96](https://github.com/carloshugoeg/koicloud/issues/96) P4 + decisión en #93). Archivo movido de `docs/tickets/w4/W4-09-demo-replay.md`.

## Qué se ve

Script determinista para repetir el happy path MCP sin LLM. Lo visible es una “conversación” reproducible que sirve como fallback de demo.

## Entradas ya decididas (no se cambian)

- Ruta propia: `scripts/demo-mcp-replay.py`.
- Secuencia fija del plan de demo: `create_pond` -> `confirm` -> `run_sql` read -> `delete_pond` -> `confirm`.
- Nombre fijo del pond: `inventario-natural`.
- Se conecta a `/mcp` con slug + password y acepta `--simulate-chat`.
- El replay debe poder correrse más de una vez sin dejar el entorno roto.
- Rama: `w1-demo-replay` (no `w4-demo-replay`).
- El trabajo de implementación sigue abierto en [#93](https://github.com/carloshugoeg/koicloud/pull/93); este PR solo mueve el ticket. Tras merge de #93 (sin ADRs), marcar `hecho`.

## Criterios de aceptación

1. El script corre contra `/mcp` y produce una transcripción legible tipo chat.
2. La secuencia y el nombre del pond coinciden exactamente con el plan sellado.
3. Una segunda ejecución no falla por residuos de la primera o limpia el estado de forma explícita.
4. Queda documentado cómo invocarlo y qué salida feliz esperar.

## No tocar

- `apps/api/app/mcp/{server.py,gate.py,prompt.py}`.
- `apps/api/app/commands/**`.
- `apps/node-agent/**`.
- `infra/**`.
- `docs/adr/**` (ticket W1-25).

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes comandos, flags, payloads, tools ni atajos al flujo de confirmación.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR. Implementación en curso: [#93](https://github.com/carloshugoeg/koicloud/pull/93).

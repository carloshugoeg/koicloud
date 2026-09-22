---
id: W4-09
workstream: W4
persona: Diego
estado: abierto
rama: w4-demo-replay
epica: "E9-07"
sprint: S4
pr:
---

# [W4-09] `scripts/demo-mcp-replay.py` (repetición determinista)

## Qué se ve

Script determinista para repetir el happy path MCP sin LLM. Lo visible es una “conversación” reproducible que sirve como fallback de demo.

## Entradas ya decididas (no se cambian)

- Ruta propia: `scripts/demo-mcp-replay.py`.
- Secuencia fija del plan de demo: `create_pond` -> `confirm` -> `run_sql` read -> `delete_pond` -> `confirm`.
- Nombre fijo del pond: `inventario-natural`.
- Se conecta a `/mcp` con slug + password y acepta `--simulate-chat`.
- El replay debe poder correrse más de una vez sin dejar el entorno roto.

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

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes comandos, flags, payloads, tools ni atajos al flujo de confirmación.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

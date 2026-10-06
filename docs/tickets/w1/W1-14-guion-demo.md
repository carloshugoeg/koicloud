---
id: W1-14
workstream: W1
persona: Carlos
estado: hecho
rama: w1-guion-demo
epica: "E9-06"
sprint: S5
pr: "main (scripts/demo-vivo.sh + docs/runbooks/demo-vivo.md)"
depends_on:
---

# [W1-14] Guion de la demo y sus tres ensayos

## Qué se ve

El guion operable de demo en vivo ya está versionado: `scripts/demo-vivo.sh` (preflight,
reset, Demo A, Demo B, all) y el puntero `docs/runbooks/demo-vivo.md`. Onboarding §9
documenta quirks Mac/VM. Este ticket **solo formaliza** ese entregable; no reescribe el
pack de presentación del Project store.

## Entradas ya decididas (no se cambian)

- Script bash 3.2–safe en `main`.
- Guion largo / fallback MCP LLM: `docs/architecture/risks-and-demo-plan.md` (W4 replay
  `demo-mcp-replay.py` es ticket aparte).
- Sin inventar VPS; Demo A/B locales con Docker en Mac o compose del repo.

## Criterios de aceptación

1. `scripts/demo-vivo.sh` existe en `main` con subcomandos
   `preflight|reset|a|sql|b|full|entrega|warm|all`.
2. `docs/runbooks/demo-vivo.md` apunta al script y documenta el guion de Entrega final,
   ensayos E1–E3 y checklist VPS (sin inventar deploy).
3. Tres ensayos previos a la demo final quedan como ritual de equipo (calendario en
   risks-and-demo-plan §7); no requieren código nuevo en este ticket.

## No tocar

Pitch, video Canva, ni archivos del pack de presentación en el store. W4 replay MCP.

## Si algo falta

Nada bloquea: el script ya está. Si alguien rompe `demo-vivo.sh`, abrir bugfix aparte.

## Referencia

`scripts/demo-vivo.sh` · `docs/runbooks/demo-vivo.md` · `docs/agent-onboarding.md` §9.

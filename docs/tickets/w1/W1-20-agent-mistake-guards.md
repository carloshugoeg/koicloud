---
id: W1-20
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-agent-mistake-guards
epica: harness
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/88"
depends_on:
---

# [W1-20] Guardias para errores repetidos de agentes

## Qué se ve

El job `guards` corre `scripts/agent_guards.py`. Falla si un ticket no coincide con su PR, si el cuerpo del PR no trae la plantilla con salida real de `make check-*`, si una página nueva pasa de 250 líneas, o si el CLI llama `Table()` fuera de `emit_table`.

Un `ship review: LGTM` queda anulado, y el job falla si es el único sobre el head, cuando se publicó antes del committer time del head, cuando se publicó a menos de 10 minutos, o cuando no responde un `ship review: changes needed` anterior. El job no mira el login ni la etiqueta `cross-workstream`.

## Entradas ya decididas (no se cambian)

- El reloj es el `committer.date` del commit en la punta del PR.
- Una mención del review anterior es su sha o el texto `changes needed`.
- Cada hallazgo numerado (`1.`, `2.`, …) pide una palabra `resolved` o `addressed`.
- `ownership` sigue siendo el job que mira las rutas. Este ticket no lo reemplaza.
- Sin cambios a OpenAPI, `schema.d.ts`, ni firmas de `commands/`.

## Criterios de aceptación

1. `python3 -m unittest scripts/test_agent_guards.py` cubre LGTM apurado, LGTM de un head viejo, LGTM que ignora hallazgos, y LGTM válido.
2. `python3 scripts/agent_guards.py tree` pasa con este ticket en `en-revision` y `pr` apuntando a #88.
3. El docstring de `scripts/agent_guards.py` describe las tres condiciones del LGTM.

## No tocar

- `packages/contracts/**`, `apps/web/src/api/schema.d.ts`, firmas de `app/commands/*`.
- `.github/workflows/deploy.yml`.
- Producción. Solo CI.

## Si algo falta

Respondé `BLOQUEADO: requiere CCR porque …` y pará.

## Referencia

Mismo estilo de job que `.github/scripts/check_ownership.py` y `.github/scripts/check_authorship.py`.

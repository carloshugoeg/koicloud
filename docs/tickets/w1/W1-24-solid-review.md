---
id: W1-24
workstream: W1
persona: Carlos Hugo Escobar
estado: en-revision
rama: w1-solid-review
epica: E10-01
sprint: S5
pr:
depends_on:
---

# [W1-24] Revisión SOLID del control plane (P7 / #96)

## Qué se ve

Existe `docs/architecture/solid-review.md` con el estado SOLID de billing, ponds, jobs, sql_console y metering (cada uno con estado y ruta de archivo). Documenta el DIP de G1 (`PaymentProvider`) y que `sql_console/router.py` importa `AsyncSession`. Los arreglos estimados >30 min tienen tickets W1-21, W1-22 y W1-23. Sin cambios de código de producción en este ticket.

## Entradas ya decididas (no se cambian)

- Ítem P7 de [#96](https://github.com/carloshugoeg/koicloud/issues/96): solo docs (+ tickets de follow-up).
- Módulos a revisar: `billing`, `ponds`, `jobs`, `sql_console`, `metering`.
- Rama `w1-solid-review` (AGENTS.md §1 Paso 5).
- No tocar OpenAPI, firmas de `commands/*`, migraciones ni código de producción.

## Criterios de aceptación

1. `docs/architecture/solid-review.md` lista los cinco módulos con estado y archivo principal.
2. G1 `PaymentProvider` DIP y la observación de `AsyncSession` en `sql_console/router.py` están documentados.
3. Refactors >30 min abiertos como tickets bajo `docs/tickets/w1/` (W1-21..W1-23) con las seis secciones.
4. El ticket aparece en `docs/tickets/w1/00-INDEX.md`; `docs/architecture/README.md` enlaza el review.
5. Diff solo bajo `docs/`; CI verde; sin merge en este ticket (revisión humana).

## No tocar

- `apps/**`, `packages/**`, `infra/**`, `.github/**`, `Makefile`.
- Contratos congelados (OpenAPI, firmas de comandos, tablas/enums).
- PR #89, #93 u otros ítems del plan #96.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

- Plan: `docs/issue-96-plan.md` (store) · [#96](https://github.com/carloshugoeg/koicloud/issues/96)
- Plantilla: `docs/tickets/W0-00-plantilla.md`

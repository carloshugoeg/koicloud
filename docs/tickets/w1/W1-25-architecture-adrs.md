---
id: W1-25
workstream: W1
persona: Carlos
estado: en-curso
rama: w1-architecture-adrs
epica: E10-02
sprint: S5
pr:
depends_on:
---

# [W1-25] ADRs A-01..A-12 en `docs/adr/`

## Qué se ve

Los doce registros de arquitectura A-01..A-12 viven en `docs/adr/001`–`012` (más `docs/adr/README.md`), cada uno con Status, Context, Decision y Consequences. El resumen de la sección 8 de `docs/architecture/system-architecture.md` apunta a esos archivos. Este ticket es el entregable P3 de [#96](https://github.com/carloshugoeg/koicloud/issues/96) (separación respecto de #93).

## Entradas ya decididas (no se cambian)

- Ruta canónica: `docs/adr/` (no `docs/architecture/adr/`); ya citada en `docs/architecture/README.md`, `repo-scaffolding.md` y `docs/WORKSTREAMS.md`.
- Identificadores A-01..A-12 y títulos de `docs/architecture/system-architecture.md` §8.
- Plantilla mínima por ADR: Status · Context · Decision · Consequences.
- Sin cambios a OpenAPI, firmas de `commands/*`, migraciones ni código de producción.
- El script `scripts/demo-mcp-replay.py` y W4-09/W1-26 quedan fuera de este ticket.

## Criterios de aceptación

1. Existen `docs/adr/001-*.md` … `docs/adr/012-*.md` y `docs/adr/README.md` con índice A-01..A-12.
2. Cada ADR trae las secciones Status, Context, Decision y Consequences.
3. El ticket aparece en `docs/tickets/w1/00-INDEX.md` con rama `w1-architecture-adrs`.
4. Diff de este ticket solo bajo `docs/adr/**` y el propio archivo de ticket (más INDEX); sin scripts de demo.
5. Tras fusionar, #93 puede dropear `docs/adr/**` y apuntar al ticket movido W1-26 para el replay.

## No tocar

- `scripts/**`, `apps/**`, `packages/**`, `infra/**`, `.github/**`.
- Contratos congelados (OpenAPI, firmas de comandos, tablas/enums).
- Implementación del demo MCP replay (sigue en #93 / W1-26).

## Si algo falta

Respondé `BLOQUEADO: requiere CCR porque …` y pará.

## Referencia

Contenido tomado de la rama `w1-adr-demo-replay` (PR #93), sin el script de replay. Misma forma de ticket que W1-20.

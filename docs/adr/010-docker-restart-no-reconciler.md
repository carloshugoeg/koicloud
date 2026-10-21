# ADR-010: docker --restart=no y reconciler propio

- **Status:** Accepted
- **Date:** 2026-10-21
- **Pack ref:** A-10 in `docs/architecture/system-architecture.md` §8

## Context

KoiCloud es un DBaaS académico con un equipo pequeño y un solo VPS de demo.
Había que fijar la forma del sistema antes de repartir workstreams.

## Decision

**docker --restart=no y reconciler propio.**

## Alternatives considered

- docker --restart=always

## Consequences

- El curador de estado somos nosotros; permite pausar/reiniciar sin que Docker levante contenedores a espaldas
- Cualquier propuesta que contradiga esta decisión abre un ADR nuevo o un CCR; no se “arregla” en silencio en un PR de feature.

# ADR-009: Consola SQL con conexión efímera por consulta

- **Status:** Accepted
- **Date:** 2026-10-21
- **Pack ref:** A-09 in `docs/architecture/system-architecture.md` §8

## Context

KoiCloud es un DBaaS académico con un equipo pequeño y un solo VPS de demo.
Había que fijar la forma del sistema antes de repartir workstreams.

## Decision

**Consola SQL con conexión efímera por consulta.**

## Alternatives considered

- Pool persistente por pond

## Consequences

- Aísla fallos; permite SET TRANSACTION READ ONLY + statement_timeout sin manchar otras requests
- Cualquier propuesta que contradiga esta decisión abre un ADR nuevo o un CCR; no se “arregla” en silencio en un PR de feature.

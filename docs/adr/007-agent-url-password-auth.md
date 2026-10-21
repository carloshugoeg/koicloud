# ADR-007: Autenticación de agente = URL secreta + password

- **Status:** Accepted
- **Date:** 2026-10-21
- **Pack ref:** A-07 in `docs/architecture/system-architecture.md` §8

## Context

KoiCloud es un DBaaS académico con un equipo pequeño y un solo VPS de demo.
Había que fijar la forma del sistema antes de repartir workstreams.

## Decision

**Autenticación de agente = URL secreta + password.**

## Alternatives considered

- OAuth 2.1 con scopes finos

## Consequences

- Alcance sellado; seguridad completa queda como V2. No se pretende equivalencia con OAuth
- Cualquier propuesta que contradiga esta decisión abre un ADR nuevo o un CCR; no se “arregla” en silencio en un PR de feature.

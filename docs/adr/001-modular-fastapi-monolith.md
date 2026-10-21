# ADR-001: Monolito modular FastAPI (no microservicios)

- **Status:** Accepted
- **Date:** 2026-10-21
- **Pack ref:** A-01 in `docs/architecture/system-architecture.md` §8

## Context

KoiCloud es un DBaaS académico con un equipo pequeño y un solo VPS de demo.
Había que fijar la forma del sistema antes de repartir workstreams.

## Decision

**Monolito modular FastAPI (no microservicios).**

## Alternatives considered

- Microservicios por dominio

## Consequences

- Ciclo de despliegue simple; transacciones compartidas entre auth/billing/ponds; el equipo no ha operado microservicios
- Cualquier propuesta que contradiga esta decisión abre un ADR nuevo o un CCR; no se “arregla” en silencio en un PR de feature.

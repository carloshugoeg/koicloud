# ADR-008: Superficies delgadas sin dominio

- **Status:** Accepted
- **Date:** 2026-10-21
- **Pack ref:** A-08 in `docs/architecture/system-architecture.md` §8

## Context

KoiCloud es un DBaaS académico con un equipo pequeño y un solo VPS de demo.
Había que fijar la forma del sistema antes de repartir workstreams.

## Decision

**Superficies delgadas sin dominio.**

## Alternatives considered

- Duplicar reglas en cada superficie

## Consequences

- Una sola fuente de verdad en app/commands evita divergencia; la misma prueba cubre Web, CLI y MCP
- Cualquier propuesta que contradiga esta decisión abre un ADR nuevo o un CCR; no se “arregla” en silencio en un PR de feature.

# ADR-005: Cola de confirmaciones (pending_confirmations) para CLI/MCP

- **Status:** Accepted
- **Date:** 2026-10-21
- **Pack ref:** A-05 in `docs/architecture/system-architecture.md` §8

## Context

KoiCloud es un DBaaS académico con un equipo pequeño y un solo VPS de demo.
Había que fijar la forma del sistema antes de repartir workstreams.

## Decision

**Cola de confirmaciones (pending_confirmations) para CLI/MCP.**

## Alternatives considered

- Enviar “eres tú” en cada request

## Consequences

- La confirmación es explícita, no depende de sesiones ni cookies; se puede expirar y auditar
- Cualquier propuesta que contradiga esta decisión abre un ADR nuevo o un CCR; no se “arregla” en silencio en un PR de feature.

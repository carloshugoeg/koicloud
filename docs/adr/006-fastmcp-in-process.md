# ADR-006: FastMCP montado en el mismo proceso API

- **Status:** Accepted
- **Date:** 2026-10-21
- **Pack ref:** A-06 in `docs/architecture/system-architecture.md` §8

## Context

KoiCloud es un DBaaS académico con un equipo pequeño y un solo VPS de demo.
Había que fijar la forma del sistema antes de repartir workstreams.

## Decision

**FastMCP montado en el mismo proceso API.**

## Alternatives considered

- Proceso MCP aparte detrás de Caddy

## Consequences

- Menos operación; comparte contexto y logging con la API. Plan B: proceso aparte (documentado si FastMCP in-process falla)
- Cualquier propuesta que contradiga esta decisión abre un ADR nuevo o un CCR; no se “arregla” en silencio en un PR de feature.

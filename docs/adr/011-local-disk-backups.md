# ADR-011: Backups como archivos en disco local

- **Status:** Accepted
- **Date:** 2026-10-21
- **Pack ref:** A-11 in `docs/architecture/system-architecture.md` §8

## Context

KoiCloud es un DBaaS académico con un equipo pequeño y un solo VPS de demo.
Había que fijar la forma del sistema antes de repartir workstreams.

## Decision

**Backups como archivos en disco local.**

## Alternatives considered

- S3 / MinIO

## Consequences

- Fuera de alcance añadir almacenamiento externo; el respaldo local basta para la demo
- Cualquier propuesta que contradiga esta decisión abre un ADR nuevo o un CCR; no se “arregla” en silencio en un PR de feature.

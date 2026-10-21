# ADR-004: Node-agent como proceso systemd separado

- **Status:** Accepted
- **Date:** 2026-10-21
- **Pack ref:** A-04 in `docs/architecture/system-architecture.md` §8

## Context

KoiCloud es un DBaaS académico con un equipo pequeño y un solo VPS de demo.
Había que fijar la forma del sistema antes de repartir workstreams.

## Decision

**Node-agent como proceso systemd separado.**

## Alternatives considered

- Ejecutar Docker desde la API

## Consequences

- Aísla la única capa con acceso al socket Docker; la API se puede reiniciar sin tocar contenedores
- Cualquier propuesta que contradiga esta decisión abre un ADR nuevo o un CCR; no se “arregla” en silencio en un PR de feature.

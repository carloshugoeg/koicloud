# ADR-003: Docker directo en un VPS (no Kubernetes)

- **Status:** Accepted
- **Date:** 2026-10-21
- **Pack ref:** A-03 in `docs/architecture/system-architecture.md` §8

## Context

KoiCloud es un DBaaS académico con un equipo pequeño y un solo VPS de demo.
Había que fijar la forma del sistema antes de repartir workstreams.

## Decision

**Docker directo en un VPS (no Kubernetes).**

## Alternatives considered

- K8s / Nomad

## Consequences

- El curso evalúa entender el provisioning; K8s lo esconde y añade operación sin beneficio de aprendizaje
- Cualquier propuesta que contradiga esta decisión abre un ADR nuevo o un CCR; no se “arregla” en silencio en un PR de feature.

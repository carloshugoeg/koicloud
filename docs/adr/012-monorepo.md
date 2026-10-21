# ADR-012: Un solo repo (monorepo) koicloud

- **Status:** Accepted
- **Date:** 2026-10-21
- **Pack ref:** A-12 in `docs/architecture/system-architecture.md` §8

## Context

KoiCloud es un DBaaS académico con un equipo pequeño y un solo VPS de demo.
Había que fijar la forma del sistema antes de repartir workstreams.

## Decision

**Un solo repo (monorepo) koicloud.**

## Alternatives considered

- Split por app

## Consequences

- Equipo pequeño; coordinar contratos entre repos añade overhead sin beneficio proporcional
- Cualquier propuesta que contradiga esta decisión abre un ADR nuevo o un CCR; no se “arregla” en silencio en un PR de feature.

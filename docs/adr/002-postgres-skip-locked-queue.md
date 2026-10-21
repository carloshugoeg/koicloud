# ADR-002: Cola en PostgreSQL con SKIP LOCKED

- **Status:** Accepted
- **Date:** 2026-10-21
- **Pack ref:** A-02 in `docs/architecture/system-architecture.md` §8

## Context

KoiCloud es un DBaaS académico con un equipo pequeño y un solo VPS de demo.
Había que fijar la forma del sistema antes de repartir workstreams.

## Decision

**Cola en PostgreSQL con SKIP LOCKED.**

## Alternatives considered

- Kafka / RabbitMQ / Redis Streams

## Consequences

- Una dependencia menos; el volumen del aula (decenas de jobs/min) sobra; el equipo ya sabe SQL
- Cualquier propuesta que contradiga esta decisión abre un ADR nuevo o un CCR; no se “arregla” en silencio en un PR de feature.

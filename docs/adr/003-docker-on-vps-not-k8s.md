# Docker en un VPS

## Status

Accepted. A-03.

## Context

El curso evalúa que el equipo entienda cómo nace un pond. Kubernetes y Nomad esconden el `docker run`. También agregan un clúster que la materia no pide operar.

## Decision

Cada pond es un contenedor Docker en un VPS de un solo nodo.

## Consequences

Hay un solo nodo. Si el VPS cae, cae el servicio. El plan de demo cubre ese día con un video y con `AGENT_MODE=mock` en la laptop del expositor.

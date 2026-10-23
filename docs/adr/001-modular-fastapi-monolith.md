# Monolito modular en FastAPI

## Status

Accepted. A-01.

## Context

Auth, billing y ponds tienen que quedar comprometidos en la misma operación. Un pond no se crea si no hay suscripción, y la suscripción vive en la misma base. Microservicios por dominio exigirían una transacción distribuida. El equipo de la materia no opera microservicios.

## Decision

El control plane es un proceso FastAPI partido en módulos. Auth, billing y ponds comparten la sesión de PostgreSQL.

## Consequences

Un deploy publica la API completa. Si el proceso cae, `/mcp` cae con él, porque el servidor MCP vive ahí. Separar un módulo exige un ADR nuevo.

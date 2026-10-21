# Reinicio de contenedores a cargo del reconciler

## Status

Accepted. A-10.

## Context

Con `docker --restart=always`, Docker vuelve a levantar un contenedor que el usuario pausó. El estado deseado deja de mandar.

## Decision

Los ponds usan `docker --restart=no`. El reconciler vuelve a encolar `start_pond` solo cuando el estado deseado es `running` y el observado es `stopped`. El reconciler no se presenta como reparación automática.

## Consequences

Pausar un pond se mantiene. El reconciler no compite con esa pausa. Si el reconciler está caído, un contenedor parado sigue parado.

# Un solo repositorio

## Status

Accepted. A-12.

## Context

El equipo es pequeño. Repositorios separados para la web, la API y la CLI obligan a versionar el contrato en cada cambio.

## Decision

Web, API, CLI, node-agent y docs viven en el repositorio `koicloud`.

## Consequences

Un PR puede tocar más de una carpeta, y cada carpeta sigue teniendo dueño. Publicar una sola app exigiría un corte que hoy no existe.

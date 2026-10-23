# FastMCP en el proceso de la API

## Status

Accepted. A-06.

## Context

El MCP tiene que ver el mismo usuario, los mismos logs y los mismos comandos que la API. Un proceso MCP separado, detrás de Caddy, duplica el deploy y el contexto.

## Decision

FastMCP va montado en el proceso de la API. La ruta pública es `/mcp`.

## Consequences

Hay una pieza menos que operar. Un bug del montaje in-process responde 500 en `/mcp`. El plan B es un proceso FastMCP separado. Quedó anotado como ADR-013 en el harness previo, y no se adopta aquí.

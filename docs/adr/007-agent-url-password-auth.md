# Acceso de agente con slug y contraseña

## Status

Accepted. A-07.

## Context

Un IDE se conecta al MCP en nombre del usuario. OAuth 2.1 con scopes finos está fuera del alcance sellado. Este acceso no es ese OAuth, y no se presenta como equivalente.

## Decision

El agente se autentica con el slug secreto y una contraseña. El gate de `/mcp` acepta `Authorization` con el esquema Basic y el valor `slug:password`. También acepta el header `X-KOI-Agent-Password`. La contraseña se guarda con argon2 en `agent_access`. La versión con scopes queda etiquetada como V2.

## Consequences

Quien tiene el slug y la contraseña actúa como el dueño. Las mutaciones siguen exigiendo `pending_confirmations`. Rotar la contraseña revoca este acceso.

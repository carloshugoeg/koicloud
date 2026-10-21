# Cola de confirmaciones

## Status

Accepted. A-05.

## Context

La CLI y el MCP pueden borrar un pond o escribir SQL. Pedir "eres tú" en el mismo request no deja una fila, no expira y se mezcla con la cookie del navegador.

## Decision

Cada mutación que llega por CLI o por MCP inserta una fila en `pending_confirmations`. El cliente muestra el `summary`. En un paso posterior llama a `confirm_action` con el token. El token expira a los 5 minutos.

## Consequences

La mutación no corre en el turno en que se propone. La fila se puede auditar y se puede descartar. La web no usa esta cola, porque el usuario ya confirmó al usar la pantalla.

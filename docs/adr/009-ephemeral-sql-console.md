# Conexión SQL efímera por consulta

## Status

Accepted. A-09.

## Context

La consola corre la consulta de un usuario y después la de otro. Un pool persistente se queda con `statement_timeout` y con el modo de la transacción anterior. El aula no pide throughput de consola.

## Decision

Cada consulta abre una conexión y la cierra al terminar. La sesión de lectura aplica `SET TRANSACTION READ ONLY` y `statement_timeout`.

## Consequences

Un fallo queda en esa conexión y no pasa a la siguiente. No hay un pool que ajustar. El costo es abrir una conexión por consulta.

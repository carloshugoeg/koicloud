# Cola de jobs en PostgreSQL

## Status

Accepted. A-02.

## Context

El node-agent reclama jobs de creación, borrado y respaldo. El aula mueve decenas de jobs por minuto. Kafka, RabbitMQ o Redis Streams sumarían un servicio que el equipo tendría que operar. El equipo ya escribe SQL.

## Decision

La cola vive en PostgreSQL. El reclamo usa `SELECT ... FOR UPDATE SKIP LOCKED`.

## Consequences

No hay un broker aparte que vigilar. El tope es el de esa consulta sobre la base del control plane. Si hacen falta más que decenas de jobs por minuto, la cola se cambia con un ADR.

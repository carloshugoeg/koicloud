# Respaldos en disco local

## Status

Accepted. A-11.

## Context

La demo necesita respaldos. S3 o MinIO agregan una cuenta y un servicio que el alcance no incluye.

## Decision

Cada respaldo es un archivo `.dump` en el disco del VPS. El respaldo de la base interna lo hace un cron del host, y se conserva 7 días.

## Consequences

Alcanza para la demo y para el aula. Si se pierde el disco, se pierden los respaldos. Moverlos a un almacén externo exige un ADR.

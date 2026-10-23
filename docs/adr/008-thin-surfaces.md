# Superficies sin reglas de dominio

## Status

Accepted. A-08.

## Context

Web, CLI y MCP tienen que demostrar la misma regla. Si cada superficie copia la regla, la demo deja de ser una prueba en tres canales.

## Decision

Las superficies no deciden dominio. Llaman a los comandos del control plane. La regla vive en `app/commands`.

## Consequences

Un cambio de regla se hace en el comando, y las tres superficies lo heredan. Si una superficie empieza a decidir por su cuenta, hay que volver a alinearla con el comando.

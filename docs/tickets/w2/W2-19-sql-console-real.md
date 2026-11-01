---
id: W2-19
workstream: W2
persona: Jason
estado: en-curso
rama: w2-sql-console-real
epica: E5-01
sprint: S5
pr:
depends_on: W2-07
---

# [W2-19] Consola SQL contra el pond real

## Qué se ve

En `/app/ponds/:id/consola`, un clic en Ejecutar manda la consulta que está en el editor. El modo lectura corre contra el Postgres del pond y no puede escribir. El historial de ese pond muestra la consulta que acaba de ejecutarse.

## Entradas ya decididas (no se cambian)

- Ruta: `/app/ponds/:id/consola`. API: `POST /ponds/{id}/sql` y `GET /ponds/{id}/sql/history`.
- Firmas de `run_sql` y `list_sql_history`. Body `{query, mode:read|write}`.
- Modo `read` en transacción de solo lectura, `statement_timeout` de 10 s, tope de 1000 filas.
- Errores de catálogo: `sql_readonly_violation` y `sql_timeout`.
- Write desde CLI o MCP sigue en `409 confirmation_required` hasta `confirm`.
- Depends on W2-07 landed. Call `run_sql` and `list_sql_history` only.

## Criterios de aceptación

1. `run_sql` en modo read devuelve las filas de un pond Postgres real. Prueba `test_run_sql_read_returns_rows_from_the_real_pond`.
2. El mismo modo rechaza un `INSERT` con `sql_readonly_violation` y no agrega la fila. Prueba `test_run_sql_read_mode_rejects_writes` y `test_sql_endpoint_read_mode_rejects_writes`.
3. `POST /ponds/{id}/sql` devuelve esas filas y `GET …/sql/history` incluye la consulta. Prueba `test_sql_endpoint_returns_pond_rows_and_history`.
4. Un solo clic en Ejecutar muestra el resultado y la consulta en el historial. Prueba `one Ejecutar click returns the pond row and records history`.

## No tocar

- `packages/contracts/**`, `apps/web/src/api/schema.d.ts`, firmas de `app/commands/*`.
- Tablas, columnas y enums.
- El código de error `pond_not_running` (no está en el catálogo).

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
solo si hay que editar un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

- W2-07 y `docs/adr/009-ephemeral-sql-console.md`.
- `docs/statechart/level2/sql-query.md`.

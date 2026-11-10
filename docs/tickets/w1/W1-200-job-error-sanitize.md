---
id: W1-200
workstream: W1
persona: Carlos
estado: hecho
rama: w1-200-job-error-sanitize
epica: E6-02
sprint: S5
pr: https://github.com/carloshugoeg/koicloud/pull/201
depends_on:
---

# [W1-200] Sanitizar last_error de los jobs

## Qué se ve

Un job que falla devuelve en `last_error` solo un código cerrado y una frase fija
en español. La salida cruda de psql, las filas del dump y las contraseñas quedan
solo en el log del servidor, redactadas.

## Entradas ya decididas (no se cambian)

- `last_error` sigue siendo un string. Sin cambios en `packages/contracts/**` ni en OpenAPI.
- Sin códigos de error nuevos en el catálogo §7.
- Las filas viejas se sanitizan al leer; la tabla no cambia.

## Criterios de aceptación

1. Un restore fallido no devuelve filas del dump ni texto de psql.
   Prueba `test_failed_restore_of_a_dump_hides_row_data`.
2. Un backup fallido no devuelve la salida del comando.
   Prueba `test_failed_backup_hides_command_output`.
3. Un fallo reportado por el node-agent no devuelve la salida del comando.
   Prueba `test_node_agent_reported_failure_hides_command_output`.
4. Una fila vieja con texto crudo no se devuelve cruda.
   Prueba `test_existing_job_row_is_not_returned_raw`.
5. `docs/gate-checklist.md` tiene la fila y una prueba plantilla.

## No tocar

- `.github/workflows/deploy.yml`.
- `packages/contracts/**` y el catálogo de `ErrorCode`.
- Las pruebas del commit `test:` 353bdf8.

## Referencia

Issue #200 y el amendment r8-7 en #96.

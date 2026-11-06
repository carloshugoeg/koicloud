---
id: W1-191
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-191-sql-console-role
epica: E5-01
sprint: S5
pr: "https://github.com/carloshugoeg/koicloud/pull/198"
depends_on:
---

# [W1-191] SQL console connects as a non-superuser role

## Qué se ve

La consola SQL abre el pond como el rol `koi_console`. Ese rol no es superusuario, es dueño del esquema `app` y no pertenece a `pg_read_server_files`, `pg_write_server_files` ni `pg_execute_server_program`. `COPY ... PROGRAM` responde 400 `sql_error` con el mensaje fijo y no ejecuta el programa. Un `INSERT` en modo read sigue en `sql_readonly_violation`. El tope de 1000 filas y el timeout de 10 segundos no cambian.

## Entradas ya decididas (no se cambian)

- `run_sql` en `apps/api/app/commands/sql.py`. La firma no cambia.
- El código `sql_error` y su mensaje fijo. No hay `ErrorCode` nuevo.
- `packages/contracts/**` no se edita.
- La contraseña del rol sale de la contraseña del pond ya cifrada en `ponds.db_password_encrypted`. No se agrega columna ni secreto al repo.
- Issue #191 y el plan #96 r8-2.

## Criterios de aceptación

1. `COPY ... PROGRAM` por `POST /api/v1/ponds/{id}/sql` responde 400 `sql_error` y no crea el archivo del programa. Prueba `test_copy_program_returns_sql_error_and_runs_nothing`.
2. En la sesión, `rolsuper` es falso y el rol no es miembro de los tres roles `pg_*_server_*`. Prueba `test_console_session_is_not_superuser_and_not_a_server_file_role`.
3. Leer y escribir el esquema de la app, y `CREATE TABLE` en modo write, siguen funcionando. Prueba `test_console_reads_and_writes_app_data_and_can_create_a_table`.
4. Modo read rechaza un `INSERT`. El tope de 1000 filas y el timeout se mantienen. Pruebas ya existentes en `tests/test_sql_real_pond.py`.
5. `docs/gate-checklist.md` tiene el ítem del rol con un template test.

## No tocar

- `packages/contracts/**` y el OpenAPI publicado.
- Firmas de `app/commands/*`.
- Tablas, columnas y enums.
- `deploy.yml`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

Issue #191, amendment r8 en #96, y el PR #180 para la forma del cuerpo.

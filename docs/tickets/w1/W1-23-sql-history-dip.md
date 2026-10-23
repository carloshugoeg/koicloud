---
id: W1-23
workstream: W1
persona: Carlos Hugo Escobar
estado: abierto
rama: w1-sql-history-dip
epica: E5-05
sprint: S5
pr:
depends_on:
---

# [W1-23] Historial SQL vía commands (DIP)

## Qué se ve

`GET /ponds/{id}/sql/history` deja de devolver el ejemplo OpenAPI y lista el historial real del actor+pond (paginado). Ningún router HTTP importa `AsyncSession` ni instancia `SqlConsoleService` directamente: delegan a `commands.sql.list_sql_history`.

## Entradas ya decididas (no se cambian)

- Rutas y schemas de `list_sql_history` / `SQLHistoryResponse` (OpenAPI congelado).
- Persistencia y truncado 4000 chars en `SqlConsoleService` / modelo `SqlHistory` (W4-06).
- `run_sql` sigue en `commands/sql.py`; este ticket no redefine el ejecutor SQL del pond.
- Observación en `docs/architecture/solid-review.md` § sql_console y en [#96](https://github.com/carloshugoeg/koicloud/issues/96).

## Criterios de aceptación

1. `commands.sql.list_sql_history` llama a `SqlConsoleService` (o equivalente) con sesión propia; ya no retorna solo `.example()`.
2. `api_v1.list_sql_history` y, si el módulo router se monta o se mantiene, `sql_console/router.py` **no** importan `AsyncSession` ni `get_session` para historial.
3. Pruebas de API: historial vacío, una página, cursor inválido con código del catálogo (o el 422 ya acordado, documentado).
4. `make check-api` verde; sin cambio de paths OpenAPI (solo comportamiento de cuerpo).

## No tocar

- Firmas públicas de otros comandos; migraciones salvo CCR si faltara columna (no debería).
- UI web de la consola (W2); solo backend.
- Lógica de parse/ejecución SQL en el data plane.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

- `docs/architecture/solid-review.md` § sql_console
- W4-06 [#78](https://github.com/carloshugoeg/koicloud/pull/78) (router/historial del módulo)
- `apps/api/app/commands/sql.py` (`list_sql_history`)

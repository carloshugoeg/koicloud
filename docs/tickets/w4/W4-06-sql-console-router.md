---
id: W4-06
workstream: W4
persona: Diego
estado: abierto
rama: w4-sql-console-router
epica: "E5-01, E5-05"
sprint: S4
pr:
---

# [W4-06] Módulo `sql_console`: router e historial

## Qué se ve

Router backend para la consola SQL web e historial. Lo visible es que el contrato HTTP existe y delega a la capa de comando ya escrita por W1.

## Entradas ya decididas (no se cambian)

- Ruta propia: `apps/api/app/modules/sql_console/**`.
- Endpoints: `POST /ponds/{id}/sql` y `GET /ponds/{id}/sql/history`.
- Delegan a `commands.run_sql` y al registrador/listador de historial.
- Las consultas guardadas se truncan a 4000 caracteres y quedan scopeadas por actor+pond.
- No se parsea SQL ni se mueve lógica de negocio al router.

## Criterios de aceptación

1. El router valida body/query y delega exactamente una vez a la capa de comando.
2. El historial pagina por pond y usuario.
3. La persistencia del historial corta a 4000 caracteres.
4. Hay pruebas de API con capa de comandos stubbeada, sin tocar `commands/sql.py`.

## No tocar

- `apps/api/app/commands/**`, en especial `commands/sql.py`.
- `apps/node-agent/**`.
- `apps/api/app/mcp/**`.
- `infra/**` y `.github/workflows/deploy.yml`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes comandos, flags, payloads, tools ni atajos al flujo de confirmación.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

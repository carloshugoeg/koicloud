---
id: W1-10
workstream: W1
persona: Carlos
estado: abierto
rama: w1-backups
epica: "E6-01, E6-02, E6-03, E6-04"
sprint: S3
pr:
depends_on:
---

# [W1-10] Respaldos diarios y restauración verificada

## Qué se ve

`GET /ponds/{id}/backups`, `POST /ponds/{id}/backups` y `POST /ponds/{id}/restore`
dejan de devolver fixtures. El node-agent ejecuta `backup_pond` / `restore_pond` contra
el driver. Un delete de pond encola respaldo `pre_delete` antes de borrar. La Web y la CLI
ven respaldos reales con `kind`, `status`, `size_bytes` y `sha256`.

## Entradas ya decididas (no se cambian)

- Firmas de `commands.backups` y OpenAPI de backups/restore.
- Jobs: `backup_pond`, `restore_pond`. Kinds: `daily`, `on_demand`, `pre_delete`.
- CLI/MCP restore usa `propose → confirm`; Web confirma tipando el nombre del pond.
- Tabla `backups` ya existe en `0001_initial`. ORM/modelo si falta se añade sin migración
  nueva salvo columnas verdaderamente ausentes.
- Scheduler diario puede ser un worker mínimo o cron documentado; no inventar VPS.

## Criterios de aceptación

1. `GET /ponds/{id}/backups` lista filas persistidas del pond dueño (vacío válido).
2. Trigger on-demand encola job `backup_pond` y crea fila `status=queued|running|succeeded`.
3. Restore encola `restore_pond` sobre un backup `succeeded` del mismo pond; otro id → error
   de contrato existente (no inventar códigos).
4. `delete_pond` encola `backup_pond` con `kind=pre_delete` antes del job de borrado.
5. `make check-api` y `make check-node-agent` verdes con prueba de backup o restore feliz.

## No tocar

OpenAPI/schemas congelados salvo regenerar con `make contracts` si un example cambia.
Pantallas W2 (`W2-08`), CLI W4, pack de presentación del store. Sin host inventado.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

`docs/architecture/interconnections.md` (backups/restore) y `docs/architecture/api-surface.md` §ponds backups.

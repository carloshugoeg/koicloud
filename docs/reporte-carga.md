# Reporte de carga (k6)

Documento de evidencia para **E10-04 / W4-08**. Los scripts viven en [`load/k6/`](../load/k6/).

## Contexto de ejecución

| Campo | Valor |
|-------|--------|
| Fecha (UTC) | 2026-10-21 (scripts aterrizados; **corrida VPS pendiente**) |
| Commit de los scripts | `075b97e` (actualizar tras la corrida real) |
| Escenarios | `login`, `list_ponds`, `create_pond` |
| Umbral RNF-01 | p95 `< 500 ms` con **20** VUs; `http_req_failed < 1%` |
| Target | `BASE_URL` (VPS demo o API local) |

## Bloqueo: corrida sobre VPS

La evidencia numérica contra el VPS de demo **espera a Carlos** (host, dominio y secretos de W1-13).
Este PR no despliega ni inventa percentiles.

Cuando el VPS esté listo:

```bash
export BASE_URL=https://<KOICLOUD_DOMAIN>
export KOI_EMAIL=demo@koicloud.dev
export KOI_PASSWORD='…'   # seed / secreto de demo, no en el repo
bash load/k6/run-all.sh
```

Pegá debajo los `*.summary.json` de `load/k6/results/<stamp>-<commit>/`.

## Resultados (pendientes de VPS)

| Escenario | p95 (ms) | errores | threshold |
|-----------|----------|---------|-----------|
| login | — | — | pendiente VPS |
| list_ponds | — | — | pendiente VPS |
| create_pond | — | — | pendiente VPS |

Si RNF-01 falla en la corrida real, **no** se relajan umbrales: se deja la salida cruda aquí.

## Runbooks operativos (W4-12)

El ticket W4-12 pide además `docs/runbooks/free-disk.md`, `restart-agent.md` y `rollback-migration.md`.
`restart-agent.md` ya está en `main`. Las otras dos rutas son **propiedad W1** en el job `ownership`; una rama `w4-` no puede crearlas sin etiqueta `cross-workstream` (prohibida en este corte). Quedan como seguimiento W1 / Carlos.

## Cómo regenerar

Ver [`load/k6/README.md`](../load/k6/README.md).

# Reporte de carga

La fecha del documento es 2026-10-21.

## Ambiente

No hay corrida contra la API. En esta máquina `http://127.0.0.1:8000` no respondió. La corrida del VPS no se hizo.

blocked: VPS URL+secrets Carlos

Este archivo no inventa percentiles. El commit de una corrida no existe porque no hubo corrida.

Umbral RNF-01, sin relajarlo. p95 de la métrica del escenario menor que 500 ms, 20 VUs, 30 s, y tasa de error del escenario igual a 0. Hace falta al menos una muestra. Los estados 200, 201, 202 y 409 de `create_pond` no cuentan como error. El script no envía token de confirmación.

| Escenario | Métrica | p95 | Errores | Umbral |
|-----------|---------|-----|---------|--------|
| login | `login_duration` | sin corrida | sin corrida | sin corrida |
| list_ponds | `list_ponds_duration` | sin corrida | sin corrida | sin corrida |
| create_pond | `create_pond_duration` | sin corrida | sin corrida | sin corrida |

## Cómo regenerar

Contra la API local, con el stack ya levantado:

```bash
export BASE_URL=http://127.0.0.1:8000
export KOI_EMAIL=demo@koicloud.dev
export KOI_PASSWORD='Sup3rSegura!2026'
bash load/k6/run-all.sh
```

Para el VPS, Carlos define `BASE_URL`. Pega aquí el `p(95)` de cada `summary.json`, la tasa de error y si el umbral pasó. Si RNF-01 falla, deja la salida cruda y no bajes el límite de 500 ms.

El detalle de las métricas está en [`load/k6/README.md`](../load/k6/README.md).

## Runbooks

W4-12 pide `docs/runbooks/free-disk.md`, ampliar `docs/runbooks/restart-agent.md` y crear `docs/runbooks/rollback-migration.md`. Esas rutas esperan un PR `w1-`. `docs/runbooks/**` es ownership de W1. Esta rama no las crea.

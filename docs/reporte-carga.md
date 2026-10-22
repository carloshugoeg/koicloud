# Reporte de carga

La fecha del documento es 2026-10-22.

## Ambiente

Corrida local contra `http://127.0.0.1:8000` (Postgres de `docker compose`;
API en host con uvicorn porque el bridge Docker entre contenedores no enruta
TCP en esta VM). Seed `demo@koicloud.dev`. k6 v2.3.0. 20 VUs, 30 s por
escenario (valores RNF-01). Scripts sin cambios: `bash load/k6/run-all.sh`.

| Campo | Valor |
|-------|-------|
| Fecha UTC | 2026-10-22T23:09:57Z |
| Commit del árbol al correr | `779efdac7afbfaad999a43dd263e5f61aec01dac` |
| Directorio de salida | `load/k6/results/20261022T230957Z-779efda/` (gitignored) |
| `BASE_URL` | `http://127.0.0.1:8000` |
| VUs / duración | 20 / 30s |

blocked: VPS URL+secrets Carlos — esta corrida **no** es evidencia RNF-01 de
demo en VPS. RNF-01 pide el VPS de demo (`docs/entrega-2`).

## Umbral RNF-01 (sin relajar)

p95 de la métrica del escenario menor que 500 ms, 20 VUs, 30 s, y tasa de
error del escenario igual a 0. Hace falta al menos una muestra. Los estados
200, 201, 202 y 409 de `create_pond` no cuentan como error. El script no
envía token de confirmación. `create_pond` usa `X-KOI-Surface: cli`
(propose → 409 `confirmation_required`).

## Resultados (corrida local 2026-10-22)

| Escenario | Métrica | p95 | Errores | Umbral p95&lt;500 | Umbral errores==0 |
|-----------|---------|-----|---------|-------------------|-------------------|
| login | `login_duration` | **1387.58 ms** | 0.00 % (523/523 ok) | **FAIL** | PASS |
| list_ponds | `list_ponds_duration` | **410.60 ms** | 0.00 % (1812/1812 ok) | PASS | PASS |
| create_pond | `create_pond_duration` | **376.76 ms** | 0.00 % (1909/1909 ok) | PASS | PASS |

### Desviación: `login`

El umbral RNF-01 de p95 &lt; 500 ms **no se aprobó** en local para `login`.
p95 = 1387.58 ms (avg 1159.82 ms, med 1160.09 ms, n = 523). La tasa de error
fue 0 %: todas las respuestas trajeron `access_token`. No se bajó el límite
de 500 ms.

Contexto: misma forma que la corrida documentada en el PR #91 (login ~1.2 s
p95 en local; list/create bajo 500 ms). El cuello está en
`POST /api/v1/auth/login` bajo 20 VUs concurrentes en esta VM (hash de
contraseña + JWT), no en fallos HTTP. La evidencia VPS sigue pendiente de
Carlos.

### Números crudos (custom metrics)

```
outdir: load/k6/results/20261022T230957Z-779efda
commit: 779efdac7afbfaad999a43dd263e5f61aec01dac
BASE_URL=http://127.0.0.1:8000  VUs=20  duration=30s

==> login
  login_duration p(95)=1387.58ms avg=1159.82ms med=1160.09ms count=523
  login_errors rate=0
  threshold p(95)<500: FAIL
  threshold rate==0: PASS

==> list_ponds
  list_ponds_duration p(95)=410.60ms avg=331.19ms med=329.05ms count=1812
  list_ponds_errors rate=0
  threshold p(95)<500: PASS
  threshold rate==0: PASS

==> create_pond
  create_pond_duration p(95)=376.76ms avg=314.73ms med=312.80ms count=1909
  create_pond_errors rate=0
  threshold p(95)<500: PASS
  threshold rate==0: PASS
```

## Cómo regenerar

Contra la API local, con Postgres arriba y API escuchando en `:8000`:

```bash
export BASE_URL=http://127.0.0.1:8000
export KOI_EMAIL=demo@koicloud.dev
export KOI_PASSWORD='Sup3rSegura!2026'
bash load/k6/run-all.sh
```

Para el VPS, Carlos define `BASE_URL`. Pega aquí el `p(95)` de cada
`summary.json`, la tasa de error y si el umbral pasó. Si RNF-01 falla en
VPS, deja la salida cruda y no bajes el límite de 500 ms.

El detalle de las métricas está en [`load/k6/README.md`](../load/k6/README.md).

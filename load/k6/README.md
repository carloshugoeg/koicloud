# Cómo correr los escenarios k6

Tres escenarios miden las rutas de demo y dejan un JSON con percentiles y el resultado del umbral.

| Escenario | Ruta | Métrica | Muestra válida |
|-----------|------|---------|----------------|
| `login` | `POST /api/v1/auth/login` | `login_duration` | 200 con `access_token` |
| `list_ponds` | `GET /api/v1/ponds` | `list_ponds_duration` | 200 |
| `create_pond` | `POST /api/v1/ponds` | `create_pond_duration` | 200, 201, 202 o 409 |

El percentil para el reporte está en `metrics.<métrica>.values` del `summary.json`, campo `p(95)`.

## Umbral

RNF-01 pide p95 menor que 500 ms con 20 VUs. El valor por defecto es 20 VUs durante 30 s. La tasa de error del escenario tiene que ser 0. No bajes el límite de 500 ms si la corrida falla.

`K6_VUS` y `K6_DURATION` cambian el tamaño de la corrida. No cambian el límite de 500 ms. Una corrida con otros valores no sirve como evidencia de RNF-01.

Sin `BASE_URL` el script aborta al arrancar. Una corrida sin muestras también falla el umbral `count>0` de `<escenario>_samples`.

## Variables

| Variable | Obligatoria | Si falta |
|----------|-------------|----------|
| `BASE_URL` | sí | la corrida aborta |
| `KOI_EMAIL` | no | `demo@koicloud.dev` |
| `KOI_PASSWORD` | no | la contraseña demo de `README.md` |

`BASE_URL` es el origen. Un ejemplo es `http://127.0.0.1:8000`. El script quita la barra final. Si el valor termina en `/api/v1`, el script también lo quita.

## Correr los tres

```bash
export BASE_URL=http://127.0.0.1:8000
export KOI_EMAIL=demo@koicloud.dev
export KOI_PASSWORD='Sup3rSegura!2026'
bash load/k6/run-all.sh
```

Un escenario solo:

```bash
export BASE_URL=http://127.0.0.1:8000
k6 run load/k6/scenarios/login.js
```

`run-all.sh` escribe `load/k6/results/<fecha>-<commit>/`. Cada escenario deja `<escenario>.summary.json` y el directorio deja `commit.txt` con el SHA completo. Si un umbral falla, k6 sale con error y el script sigue con el siguiente escenario. Al final el script sale con error si alguno falló.

Commitea ese directorio solo después de una corrida contra la API real. No commitees la salida de un stub.

## create_pond

El escenario envía `X-KOI-Surface: cli`. La API responde 409 `confirmation_required` y no crea el pond. El script no envía `X-KOI-Confirm-Token` y no llama a confirm. 200, 201, 202 y 409 cuentan como muestra de latencia. Cualquier otro estado cuenta como error.

`list_ponds` y `create_pond` hacen login una vez en `setup`. Esa llamada no entra en la métrica del escenario.

## VPS

No despliegues desde este directorio. La URL del VPS y los secretos los tiene Carlos.

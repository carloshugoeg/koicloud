---
id: QI-01
workstream: W1
persona: Carlos
estado: en-revision
rama: qi-infra-caddy-worker
epica: E10-02
sprint: S4
pr: https://github.com/carloshugoeg/koicloud/pull/186
depends_on:
---

# [QI-01] Caddy sirve la SPA en /app y el worker pasa el healthcheck

## Qué se ve

Recargar `https://<host>/app/ponds/<id>` devuelve `app.html` con estado 200.
Un archivo que existe bajo `/app` se entrega tal cual.
`/api` sigue yendo al proxy y no devuelve la SPA.
El contenedor `worker` queda healthy. Su healthcheck no llama a `pgrep`.

## Entradas ya decididas (no se cambian)

- Los dos sitios viven en `infra/Caddyfile` y `infra/Caddyfile.http`.
- La raíz de archivos es `/srv/koicloud/web`. El shell de la SPA es `app.html`.
  La portada sigue en `index.html`.
- El bloque nuevo es `handle /app*` con `try_files {path} /app.html` y `file_server`,
  el mismo orden que el `handle` de la portada.
- `handle /api/*` no se mueve.
- La imagen del worker es `apps/api/Dockerfile` (`FROM python:3.12-slim`). Esa imagen
  no trae `procps`.
- El healthcheck lee `/proc/1/cmdline` con el `python3` de la imagen y exige la cadena
  `app.workers`. Esa cadena está en el comando del servicio, también durante el
  `sleep 3600`.
- `deploy.sh` copia el build a `/srv/koicloud/web`, no a un directorio `web/` del repo.

## Criterios de aceptación

1. `GET /app/ponds/x` contra `infra/Caddyfile.http` responde 200 y el cuerpo de `app.html`.
   `GET /app/ponds/real.txt` responde el archivo. `GET /assets/mark.js` responde el asset.
   `GET /` responde `index.html`. `GET /api/v1/health` no responde la SPA.
2. `caddy validate` acepta `infra/Caddyfile` y `infra/Caddyfile.http`.
3. Los dos archivos declaran `handle /app*` con `try_files {path} /app.html`.
4. El healthcheck del worker, ejecutado en `python:3.12-slim`, sale 0 cuando pid 1
   tiene `app.workers` en su línea de comandos, y sale distinto de 0 cuando no.
5. `npm run pregate` termina en verde.

## No tocar

`.github/workflows/deploy.yml`. `packages/contracts/**`. Código de `apps/`.
El script de la fase de prueba `infra/scripts/check-caddy-spa-worker.sh`, salvo que
el fallo demuestre que la prueba está mal.

## Si algo falta

`BLOQUEADO: requiere CCR porque …` solo si hay que editar un contrato congelado.
`BLOQUEADO: requiere ticket para Wn` solo si hay que editar un archivo de otro
workstream. Si un `depends_on` no está `hecho` o `cerrado`, la respuesta es
`ESPERA`, no CCR.

## Referencia

`infra/Caddyfile`. `infra/docker-compose.prod.yml` servicio `worker`.
`apps/web/vercel.json` (el fallback de preview ya es `/app.html`).
`infra/scripts/check-prod-compose.sh`.

# Caddy

Plantilla: `infra/Caddyfile`. Sirve la SPA desde `/srv/koicloud/web`, hace proxy de
`/api/*`, `/mcp`, `/docs`, `/openapi.json` y `/health` a `api:8000`, y responde
**403** a `/internal/*`.

Sin un DNS real apuntando al host, Let's Encrypt no emite certificado. No uses
`koicloud.example` en un VPS inventado.

```bash
docker compose --env-file infra/env/prod.env -f infra/docker-compose.prod.yml restart caddy
```

Si el cert venció o el contenedor murió: mismo comando. El runbook de deploy
(`deploy.md`) cubre el cableado inicial.

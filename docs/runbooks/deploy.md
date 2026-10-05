# Deploy (cuando exista un host)

No hay VPS del equipo todavía. Este runbook no nombra IP ni DNS reales.
El placeholder de arquitectura `koicloud.example` **no** es un dominio nuestro.

## Qué deja W1-13 listo en el repo

- `infra/docker-compose.prod.yml` — `db`, `api`, `worker`, `caddy`
- `infra/Caddyfile` — TLS (ACME), `/api`, `/mcp`, estáticos, 403 a `/internal/*`
- `infra/koicloud-agent.service` — node-agent fuera del compose
- `infra/scripts/deploy.sh` — se niega a correr con placeholders
- `.github/workflows/deploy.yml` — no hace SSH hasta que existan variables/secretos

Health post-deploy: `GET /health` o `GET /api/v1/health`.

## Lo que Carlos tiene que entregar para cablear

1. **Host:** usuario SSH + hostname o IP reales (el que pague el curso/equipo).
2. **DNS:** un nombre que apunte a ese host (`A`/`AAAA`). Sin eso Caddy no saca certificado.
3. **SSH:** clave de deploy y `known_hosts` (huella del servidor).
4. **GitHub (repo `carloshugoeg/koicloud`):**
   - Variables: `KOICLOUD_DEPLOY_HOST`, `KOICLOUD_DEPLOY_USER`, `KOICLOUD_DOMAIN`, `KOICLOUD_DEPLOY_SSH_KNOWN_HOSTS`
   - Secreto: `KOICLOUD_DEPLOY_SSH_KEY`
5. **Archivo en el host** `infra/env/prod.env` copiado desde `infra/env/prod.env.example` con secretos reales (`JWT_SECRET`, `NODE_TOKEN`, `POSTGRES_PASSWORD`, `POND_PASSWORD_KEY`, `NODE_PUBLIC_HOST` = el hostname público real).
6. **Layout en el host:** clone en `/srv/koicloud`, `uv` instalado, Docker Engine + compose, unit copiada a `/etc/systemd/system/koicloud-agent.service`.
7. **Firewall:** `22`, `80`, `443`, `15000–15999` (architecture §5). Nada más.

Hasta que esos campos existan: el ticket **sigue abierto**. No fingir deploy.

## Cuando el host ya esté

```bash
sudo mkdir -p /srv/koicloud /var/lib/koicloud/{invoices,backups,ponds} /srv/koicloud/web
# clone del repo en /srv/koicloud
cp infra/env/prod.env.example infra/env/prod.env
# editar prod.env — sin placeholders
sudo cp infra/koicloud-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now koicloud-agent
bash infra/scripts/deploy.sh
curl -fsS "https://${KOICLOUD_DOMAIN}/health"
```

Cron sugerido (dump de la base interna, 7 días):

`0 3 * * * /srv/koicloud/infra/scripts/backup-internal-db.sh`

## Comprobar artefactos sin host

```bash
bash infra/scripts/check-prod-compose.sh
```

Puntero demo local (no es producción): [`demo-vivo.md`](./demo-vivo.md).

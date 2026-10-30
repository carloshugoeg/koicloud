# Despliegue

Manual técnico (sección Despliegue). Cumple ENTREGA-2 §6.3: un dominio, Caddy
(`/` · `/api/*` · `/mcp`), API/worker/db en Compose, node-agent con socket Docker,
ponds en `15000-15999`. Decisión de host: [ADR 013](../adr/013-oracle-always-free-sslip.md)
(Oracle Always Free + sslip.io, costo $0). Topología Docker: [ADR 003](../adr/003-docker-on-vps-not-k8s.md).

**No hay VM cableada todavía.** Este runbook no inventa IP. No ejecutes un deploy
contra producción desde el agente. Cuando exista la VM, reutilizá
`.github/workflows/deploy.yml` (SSH + Docker + Caddy).

## 1. Crear la VM (Oracle Cloud Always Free)

1. Cuenta Oracle Cloud Always Free.
2. Compute → Create instance.
   - **Shape:** VM.Standard.A1.Flex (Ampere ARM), 1–2 OCPU, 6–12 GB RAM (dentro del free tier).
   - **Image:** Ubuntu 22.04 o 24.04 (aarch64).
   - **Network:** VCN por defecto con IP pública.
   - **SSH:** subí una clave; guardá la privada fuera del repo.
3. Anotá la **IP pública**. Hostname sin dominio de pago:
   - `KOICLOUD_DOMAIN=<ip>.sslip.io` (o `<ip>.nip.io`).
   - `NODE_PUBLIC_HOST` = el mismo valor (o la IP si los clientes SQL conectan por IP).

## 2. Abrir puertos (VCN + iptables)

En la **Security List** (o NSG) de la VCN, ingress:

| Puerto | Protocolo | Uso |
|--------|-----------|-----|
| 22 | TCP | SSH (restringí a tu IP si podés) |
| 80 | TCP | Caddy HTTP → ACME |
| 443 | TCP | Caddy HTTPS |
| 15000-15999 | TCP | Ponds Postgres (ENTREGA-2 §6.3) |

En la VM (iptables/nftables o `ufw`):

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 15000:15999/tcp
sudo ufw enable
```

## 3. Instalar Docker y herramientas

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git curl rsync
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"   # re-login
curl -LsSf https://astral.sh/uv/install.sh | sh
# Node 22 + pnpm 9 para el build de apps/web en el host (deploy.sh)
```

## 4. Variables de entorno (nombres y cómo generarlas)

Copiá `infra/.env.production.example` → `infra/env/prod.env` en el host.
**Nunca** commits `prod.env`. Valores reales no van en el repo.

| NAME | Cómo generar el valor |
|------|------------------------|
| `POSTGRES_USER` | Elegí un usuario (ej. `koi`). |
| `POSTGRES_PASSWORD` | `openssl rand -base64 32` |
| `POSTGRES_DB` | Nombre de la DB interna (ej. `koicloud`). |
| `DATABASE_URL` | `postgresql+asyncpg://USER:PASSWORD@db:5432/DB` con los tres de arriba. |
| `JWT_SECRET` | `openssl rand -base64 48` — **no** el default `koicloud-dev-jwt-secret-change-me`. |
| `REFRESH_TTL_DAYS` | Entero (ej. `30`). |
| `POND_PASSWORD_KEY` | Clave Fernet: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` — **no** el default de desarrollo. |
| `AGENT_MODE` | `docker` (ponds reales). Ver `docker-compose.docker-agent.yml` y la unit systemd. |
| `NODE_ID` | Identificador estable (ej. `node-prod`). |
| `NODE_TOKEN` | `openssl rand -hex 32` — **no** `koicloud-node-token`. |
| `KOICLOUD_DOMAIN` | `<ip-pública>.sslip.io` o `<ip-pública>.nip.io`. |
| `NODE_PUBLIC_HOST` | Igual que el dominio o la IP pública. |
| `POND_PORT_RANGE_START` | `15000` |
| `POND_PORT_RANGE_END` | `15999` |
| `MCP_ENABLED` | `true` o `false`. |
| `MCP_DEMO_PASSWORD` | `openssl rand -base64 24` — **no** `koicloud-demo`. |
| `EMAIL_PROVIDER` | Proveedor real (nunca `console` en production). |
| `PAYMENT_PROVIDER` | `simulated` está bien para el curso si el runbook de billing lo permite; no lo dejes vacío. |
| `INVOICE_DIR` | `/var/lib/koicloud/invoices` |
| `BACKUP_DIR` | `/var/lib/koicloud/backups` |
| `INTERNAL_API_URL` | `http://127.0.0.1:8000/internal/v1` (agent en el host). |

Compose fija `ENVIRONMENT=production`. Al arrancar, la API rechaza
`JWT_SECRET` / `POND_PASSWORD_KEY` / `NODE_TOKEN` / `MCP_DEMO_PASSWORD` si
siguen en el default de código.

## 5. GitHub Actions (vars / secrets)

Repo → Settings → Secrets and variables. **No** pegues valores aquí en docs.

| Tipo | Nombre | Contenido |
|------|--------|-----------|
| Variable | `KOICLOUD_DEPLOY_HOST` | IP o hostname SSH de la VM |
| Variable | `KOICLOUD_DEPLOY_USER` | Usuario SSH (ej. `ubuntu`) |
| Variable | `KOICLOUD_DOMAIN` | `<ip>.sslip.io` |
| Variable | `KOICLOUD_DEPLOY_SSH_KNOWN_HOSTS` | Salida de `ssh-keyscan -H <host>` |
| Secret | `KOICLOUD_DEPLOY_SSH_KEY` | Clave privada PEM de deploy |

Workflow: `.github/workflows/deploy.yml`. Sin estas cinco entradas el job
`waiting-for-host` documenta la espera y **no** hace SSH.

## 6. Primer deploy (en la VM)

```bash
sudo mkdir -p /srv/koicloud /var/lib/koicloud/{invoices,backups,ponds} /srv/koicloud/web
sudo chown -R "$USER:$USER" /srv/koicloud /var/lib/koicloud
cd /srv
git clone https://github.com/carloshugoeg/koicloud.git koicloud
cd /srv/koicloud
cp infra/.env.production.example infra/env/prod.env
# Editá prod.env con los valores de la tabla (§4). AGENT_MODE=docker.
sudo cp infra/koicloud-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now koicloud-agent
bash infra/scripts/deploy.sh
curl -fsS "https://${KOICLOUD_DOMAIN}/health"
curl -fsS "https://${KOICLOUD_DOMAIN}/api/v1/health"
```

Ponds reales: la unit ya pone `AGENT_MODE=docker`. El overlay local
`docker-compose.docker-agent.yml` documenta el mismo modo para demos en laptop.

## 7. Actualizar (segundo deploy y siguientes)

En el host:

```bash
cd /srv/koicloud
bash infra/scripts/deploy.sh
```

O push a `main` con las vars/secrets de §5: el workflow SSH ejecuta el mismo script.
`deploy.sh` es idempotente (compose up --build + migrate).

## 8. Rollback

1. **App / imágenes:** en el host, `git -C /srv/koicloud checkout <sha-bueno>` y
   `bash infra/scripts/deploy.sh`.
2. **Migración Alembic:** seguí [`rollback-migration.md`](./rollback-migration.md).
3. **Agent:** [`restart-agent.md`](./restart-agent.md).
4. **Disco:** [`free-disk.md`](./free-disk.md).

## 9. Artefactos en el repo (sin host)

- `infra/docker-compose.prod.yml` — `db`, `api`, `worker`, `caddy` (bases multi-arch ARM)
- `infra/Caddyfile` — TLS; hostname desde `KOICLOUD_DOMAIN` (sslip.io/nip.io OK)
- `infra/koicloud-agent.service` — node-agent fuera del compose, `AGENT_MODE=docker`
- `infra/scripts/deploy.sh` — se niega a correr con placeholders
- `.github/workflows/deploy.yml` — gate hasta que existan vars/secrets
- `docs/adr/013-oracle-always-free-sslip.md` — host $0 vs Render/Neon

Comprobar sin VM:

```bash
npm run pregate
# o: bash infra/scripts/check-oracle-deploy-ready.sh && make check-infra
```

Hasta que la VM exista y esté cableada, el ticket W1-13 puede seguir en revisión
de **preparación**; el deploy real no se finge.

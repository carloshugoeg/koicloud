# Manual técnico de KoiCloud

Documento operativo para instalar, configurar y operar el monorepo.
No redefine contratos. Los contratos viven en [`architecture/`](./architecture/).

**Audiencia.** Integrantes del Equipo KoiCloud y agentes que levantan el stack.
**Fuente de verdad.** Pack en [`architecture/`](./architecture/). Resumen vivo en [`ARCHITECTURE.md`](./ARCHITECTURE.md).

---

## 1. Instalación (máquina limpia)

### 1.1 Prerrequisitos

Instalá estas herramientas antes de clonar. Sin ellas `make up` y `make check` fallan.

| Herramienta | Para qué |
|-------------|---------|
| Git | Clonar el repo |
| Docker Engine + Compose plugin | `make up`, ponds reales |
| Python 3.12+ y [`uv`](https://docs.astral.sh/uv/) | API, CLI, node-agent, tests |
| Node.js 22+ y [`pnpm`](https://pnpm.io/) | Web y `make contracts` |
| `psql` (opcional) | Probar un pond local |

En macOS, si el Postgres del host ya usa el puerto **5432**, remapeá el Compose con
`KOI_DB_HOST_PORT` (ver [`agent-onboarding.md`](./agent-onboarding.md) §9 y
[`runbooks/demo-vivo.md`](./runbooks/demo-vivo.md)).

### 1.2 Clonar y levantar

```bash
git clone https://github.com/carloshugoeg/koicloud.git
cd koicloud

# Identidad real de GitHub (nunca "Equipo KoiCloud" como autor)
git config user.name  "Tu Nombre"
git config user.email "tu-correo-de-github"

cp .env.example .env   # opcional en host; Compose ya monta .env.example

make up
# Esperá health: GET http://127.0.0.1:8000/api/v1/health → 200

make migrate
make seed
```

`make seed` ya corre migrate primero. Credenciales demo tras el seed:

- Correo: `demo@koicloud.dev`
- Contraseña: `Sup3rSegura!2026`

### 1.3 Comprobar que el control plane responde

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health
curl -fsS http://127.0.0.1:8000/api/v1/plans
```

Pond de demostración sin VPS:

```bash
make pond-demo
psql "postgresql://postgres:local-pond-dev-only@127.0.0.1:15432/inventario_demo"
```

Demo de producto de extremo a extremo (Compose + DockerDriver):

```bash
bash scripts/demo-vivo.sh b
```

Detalle: [`runbooks/local-pond.md`](./runbooks/local-pond.md) y
[`runbooks/demo-vivo.md`](./runbooks/demo-vivo.md).

### 1.4 Checks por área

```bash
make check-api
make check-web
make check-cli
make check-node-agent
make check-infra
# o todo: make check
```

### 1.5 Diagramas de contexto

| Diagrama | Qué muestra |
|----------|-------------|
| [`architecture/diagrams/01-componentes.mmd`](./architecture/diagrams/01-componentes.mmd) | Control plane, data plane, superficies |
| [`architecture/diagrams/02-despliegue.mmd`](./architecture/diagrams/02-despliegue.mmd) | Topología de un solo nodo |
| [`architecture/diagrams/03-trust-boundaries.mmd`](./architecture/diagrams/03-trust-boundaries.mmd) | Límites de confianza |
| [`architecture/diagrams/04-ciclo-desired-observed.mmd`](./architecture/diagrams/04-ciclo-desired-observed.mmd) | Desired vs observed |

Lectura completa: [`architecture/system-architecture.md`](./architecture/system-architecture.md).

---

## 2. Variables de entorno

### 2.1 Desarrollo (Compose)

Plantilla: [`.env.example`](../.env.example).
Compose la monta en `api`, `worker` y `node-agent`.
No commitees secretos reales.

| Variable | Rol | Valor de ejemplo en `.env.example` |
|----------|-----|-------------------------------------|
| `DATABASE_URL` | Postgres del control plane (asyncpg) | `postgresql+asyncpg://koi:koi@db:5432/koicloud` |
| `JWT_SECRET` | Firma de access tokens | `change-me` (reemplazar fuera de demo) |
| `REFRESH_TTL_DAYS` | Vida del refresh token | `30` |
| `POND_PASSWORD_KEY` | Clave Fernet de passwords de ponds | clave de dev en el ejemplo |
| `AGENT_MODE` | `mock` (CI/dev) o `docker` (socket real) | `mock` |
| `NODE_ID` | Identidad del node-agent | `node-local` |
| `NODE_TOKEN` | Auth del agent hacia `/internal/v1` | `change-me` |
| `KOICLOUD_DOMAIN` | Dominio público (placeholder hasta host real) | `koicloud.example` |
| `NODE_PUBLIC_HOST` | Host que ven los clientes del pond | `127.0.0.1` |
| `POND_PORT_RANGE_START` / `END` | Rango publicado de ponds | `15000`–`15999` |
| `MCP_ENABLED` | Monta el servidor MCP | `true` |
| `EMAIL_PROVIDER` | `console` (dev) o `resend` (prod) | `console` |
| `INVOICE_DIR` | PDFs de factura en disco | `/var/lib/koicloud/invoices` |
| `BACKUP_DIR` | Respaldos de ponds | `/var/lib/koicloud/backups` |
| `KOI_DB_HOST_PORT` | Puerto host → Postgres Compose | `5432` por defecto |

Defaults adicionales del Settings de la API (si no vienen en env):
`CONFIRM_TTL_SECONDS` (300), `ACCESS_TOKEN_TTL_MINUTES` (15).
Código: `apps/api/app/core/config.py`.

### 2.2 Producción

Plantilla: [`infra/env/prod.env.example`](../infra/env/prod.env.example).
Copiá a `infra/env/prod.env` **en el host**. No lo subas al repo.

Además de las variables de desarrollo, prod exige:

| Variable | Rol |
|----------|-----|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Credenciales del servicio `db` en Compose prod |
| `INTERNAL_API_URL` | URL que usa el node-agent hacia la API interna |
| `AGENT_MODE=docker` | Ponds reales en el host |
| `NODE_PUBLIC_HOST` | Hostname o IP pública real (no placeholder) |

Checklist de secretos mínimos antes del primer start:
`JWT_SECRET`, `NODE_TOKEN`, `POSTGRES_PASSWORD`, `POND_PASSWORD_KEY`, `NODE_PUBLIC_HOST`.

### 2.3 CLI

| Variable | Rol | Default |
|----------|-----|---------|
| `KOICLOUD_BASE_URL` | Prefijo `/api/v1` que llama la CLI | `http://127.0.0.1:8000/api/v1` |
| `KOICLOUD_CONFIG_PATH` | Archivo de tokens | `~/.config/koicloud/config.json` |

### 2.4 Cómo detectar un env faltante

Un tercero en máquina limpia puede fallar a propósito y anotar el síntoma:

1. Borrá o comentá una variable requerida en `.env` / `prod.env`.
2. Reiniciá el servicio (`docker compose up -d api` o el unit del agent).
3. Anotá el error de arranque o el `code` JSON de `/api/v1/*`.
4. Restaurá el valor desde la plantilla correspondiente.

Si falta un paso de install no listado arriba, abrí issue o CCR. No inventes flags.

---

## 3. Deploy

No hay VPS del equipo cableado todavía.
El dominio de arquitectura `koicloud.example` **no** es un dominio nuestro.
Runbook canónico: [`runbooks/deploy.md`](./runbooks/deploy.md).
Diagrama: [`architecture/diagrams/14-deploy.mmd`](./architecture/diagrams/14-deploy.mmd).
Flujo narrado: [`architecture/interconnections.md`](./architecture/interconnections.md) §11.

### 3.1 Artefactos en el repo

| Artefacto | Rol |
|-----------|-----|
| `infra/docker-compose.prod.yml` | `db`, `api`, `worker`, `caddy` |
| `infra/Caddyfile` | TLS, `/api`, `/mcp`, estáticos; 403 a `/internal/*` |
| `infra/koicloud-agent.service` | node-agent fuera del Compose |
| `infra/scripts/deploy.sh` | Se niega a correr con placeholders |
| `.github/workflows/deploy.yml` | No hace SSH hasta tener variables y secretos |

### 3.2 Lo que hace falta fuera del repo

1. Host con SSH (usuario + hostname o IP).
2. DNS `A`/`AAAA` al host.
3. Clave de deploy y `known_hosts`.
4. Variables y secreto en GitHub (`KOICLOUD_DEPLOY_HOST`, `KOICLOUD_DEPLOY_USER`,
   `KOICLOUD_DOMAIN`, `KOICLOUD_DEPLOY_SSH_KNOWN_HOSTS`, `KOICLOUD_DEPLOY_SSH_KEY`).
5. `infra/env/prod.env` en el host, sin placeholders.
6. Layout: clone en `/srv/koicloud`, `uv`, Docker Engine, unit systemd del agent.
7. Firewall: `22`, `80`, `443`, `15000–15999`.

Hasta que eso exista, el ticket de cableado (W1-13) sigue abierto. No fingir deploy.

### 3.3 Cuando el host ya esté

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

Comprobar artefactos **sin** host:

```bash
bash infra/scripts/check-prod-compose.sh
# o: make check-infra
```

---

## 4. MCP

Montaje, gate y tools mutantes son de W1.
Contrato: [`architecture/api-surface.md`](./architecture/api-surface.md) §4.
Diagrama de confirmación: [`architecture/diagrams/07-flujo-mcp-confirm.mmd`](./architecture/diagrams/07-flujo-mcp-confirm.mmd).
Código: `apps/api/app/mcp/`.

### 4.1 Endpoint y auth

- Base: `https://<KOICLOUD_DOMAIN>/mcp` (local: `http://127.0.0.1:8000/mcp`).
- Auth de la gate mínima: Basic `slug:password` o header `X-KOI-Agent-Password`.
- Tras `make seed`, el demo agent usa slug/password de Settings
  (`MCP_DEMO_SLUG` / `MCP_DEMO_PASSWORD`, defaults `demo-agent` / `koicloud-demo`).
- Desactivá el montaje con `MCP_ENABLED=false`.

### 4.2 Tools (contrato)

La tabla canónica está en [`architecture/api-surface.md`](./architecture/api-surface.md) §4.
Incluye lecturas (`whoami`, `list_ponds`, `get_pond`, …) y mutaciones
(`create_pond`, `delete_pond`, `restore_backup`, `run_sql` en modo write, …).

Regla operativa:

1. Tool de solo lectura: se ejecuta directo.
2. Tool mutante: la API responde `409` / `confirmation_required` con `summary` y `token`.
3. El humano aprueba el `summary`.
4. Solo entonces se llama `confirm_action(token=…)`.
5. Nunca inventes un token ni reescribas el `summary`.

Prompt del server: `apps/api/app/mcp/prompt.py`
(también citado en `api-surface.md` §4).

### 4.3 Info HTTP auxiliar

`GET /mcp` (con gate) describe tools de lectura y mutación según el router MCP.
Para el mapa completo de tools → commands, usá el pack, no este manual.

---

## 5. CLI

Paquete: `apps/cli` (entrypoint `koicloud`).
Mapa comando → API: [`architecture/api-surface.md`](./architecture/api-surface.md) §5.
Diagrama de confirmación: [`architecture/diagrams/06-flujo-cli-confirm.mmd`](./architecture/diagrams/06-flujo-cli-confirm.mmd).

### 5.1 Instalar la CLI en el host

```bash
cd apps/cli
uv sync
uv run koicloud --help
```

Apuntá a tu API:

```bash
export KOICLOUD_BASE_URL=http://127.0.0.1:8000/api/v1
uv run koicloud login --email demo@koicloud.dev --password 'Sup3rSegura!2026'
uv run koicloud whoami
```

Tokens quedan en `~/.config/koicloud/config.json` (o `KOICLOUD_CONFIG_PATH`).

### 5.2 Convenciones

- Mutaciones CLI usan `propose → confirm` (mismo contrato que MCP).
- `koicloud confirm <token>` consume un pendiente.
- `koicloud confirm cancel <token>` lo descarta.
- `--yes <token>` pasa el token en el mismo comando (scripts).
- `-o json` fuerza JSON. Default: tablas con `rich`.
- Sin sesión, la CLI sale con código **`1`** y el mensaje
  `Primero corré \`koicloud login\``.

Algunos subcomandos aún están en tickets W4-03…W4-05
(`exit_unimplemented` hasta que aterricen).
El mapa de §5 del pack es el contrato. No inventes flags.

### 5.3 Flujos de referencia

| Flujo | Diagrama / doc |
|-------|----------------|
| Crear pond (Web) | [`architecture/diagrams/05-flujo-crear-pond-web.mmd`](./architecture/diagrams/05-flujo-crear-pond-web.mmd) |
| Mutar + confirmar (CLI) | [`architecture/diagrams/06-flujo-cli-confirm.mmd`](./architecture/diagrams/06-flujo-cli-confirm.mmd) |
| Cola de jobs | [`architecture/diagrams/08-cola-jobs.mmd`](./architecture/diagrams/08-cola-jobs.mmd) |
| Backup / restore | [`architecture/diagrams/11-backup-restore.mmd`](./architecture/diagrams/11-backup-restore.mmd) |

---

## 6. Exportar este manual a PDF

Mecanismo acordado del repo (igual que Entrega 2): `pandoc`.

```bash
# Desde la raíz del monorepo
pandoc docs/manual-tecnico.md \
  -o docs/manual-tecnico.pdf \
  --from markdown \
  --pdf-engine=xelatex \
  -V geometry:margin=2cm \
  --resource-path=docs
```

Si no tenés XeLaTeX, generá HTML y abrilo en el navegador (Imprimir → PDF):

```bash
pandoc docs/manual-tecnico.md \
  -o docs/manual-tecnico.html \
  --from markdown \
  --standalone \
  --resource-path=docs
```

Comprobá que las tablas de variables y los bloques de código no se corten.
No commitees el PDF generado salvo que un ticket de entrega lo pida.

---

## 7. Verificación por un tercero (máquina limpia)

Usá esta lista en un checkout nuevo. Marcá fallos con el síntoma exacto.

1. Instalá prerrequisitos de §1.1. No asumas `uv` ni Docker ya presentes.
2. Seguí §1.2 hasta `curl` de `/api/v1/health` en verde.
3. Corré `make seed` y login demo (Web o CLI).
4. Compará `.env` / `prod.env` contra las tablas de §2. Anotá cualquier variable
   que el arranque exija y no aparezca en la plantilla.
5. Corré `make check-infra` (sin host) y leé [`runbooks/deploy.md`](./runbooks/deploy.md).
6. Abrí `/mcp` con la gate demo y listá tools. Contrastá con `api-surface.md` §4.
7. Instalá la CLI (§5.1), `login`, `whoami`. Probá un comando de lectura.
8. Exportá PDF o HTML (§6) y revisá tablas y fences.

Si un paso falla por un prerrequisito oculto, reportalo contra este archivo.
No inventes el comando que “debería” existir.

---

## 8. Índice de fuentes (no copiar, enlazar)

| Tema | Documento |
|------|-----------|
| Visión y no-goals | [`architecture/vision-and-constraints.md`](./architecture/vision-and-constraints.md) |
| Arquitectura de sistema | [`architecture/system-architecture.md`](./architecture/system-architecture.md) |
| Flujos | [`architecture/interconnections.md`](./architecture/interconnections.md) |
| Modelo de datos | [`architecture/data-model.md`](./architecture/data-model.md) |
| API / CLI / MCP | [`architecture/api-surface.md`](./architecture/api-surface.md) |
| Scaffolding y ownership | [`architecture/repo-scaffolding.md`](./architecture/repo-scaffolding.md) |
| Dependencias | [`architecture/dependencies.md`](./architecture/dependencies.md) |
| Diagramas Mermaid | [`architecture/diagrams/`](./architecture/diagrams/) |
| Deploy | [`runbooks/deploy.md`](./runbooks/deploy.md) |
| Onboarding de agentes | [`agent-onboarding.md`](./agent-onboarding.md) |
| Workstreams | [`WORKSTREAMS.md`](./WORKSTREAMS.md) |

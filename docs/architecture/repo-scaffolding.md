# Repo scaffolding

Este documento fija la estructura exacta del repositorio de implementación. No crea el repo (eso se hace después, según [`feature-breakdown.md`](./feature-breakdown.md) §Fase 0); solo describe qué debe existir y cómo se organiza.

---

## 1. Nombre y forma

- **Repositorio de documentos (ya existe):** [`carloshugoeg/koicloud-entrega-2`](https://github.com/carloshugoeg/koicloud-entrega-2). Solo lleva la Entrega 2 (diseño). No se mezcla con código.
- **Repositorio de implementación (a crear):** `carloshugoeg/koicloud` — nombre corto, coincide con la marca del producto. Alternativa aceptable: `carloshugoeg/koicloud-platform` si se quiere subrayar el papel del repo. El equipo decide en Fase 0; el resto del pack asume `koicloud`.
- **Forma:** **monorepo único** con `apps/*`, `packages/*`, `infra/`, `docs/`, `load/`, `scripts/`. Ver §3 para el árbol exacto.

Justificación de monorepo (frente a repos separados por app):

- Contratos (`packages/contracts/openapi.json`) se generan a partir del backend y consumen desde la web y la CLI. Un solo repo elimina la coordinación de versiones de contrato entre repos.
- El equipo es pequeño (cuatro personas). El overhead de gobernar cuatro repos supera el beneficio.
- La CI puede correr una sola vez sobre el conjunto y bloquear PRs antes de fusionar.

Justificación de **no** usar herramientas de monorepo (Turborepo/Nx/Rush):

- Solo hay dos ecosistemas (Python con `uv`, Node con `pnpm`). Cada uno se orquesta con Makefile + workflow directo.
- Añadir Turbo/Nx duplica la curva de aprendizaje del equipo por beneficio marginal.

---

## 2. Convención de branches y commits

| Regla | Detalle |
|-------|---------|
| Rama base | `main` (protegida; nunca push directo) |
| Rama por ticket | `w<N>-<slug>` en kebab-case — `w2-detalle-pond`. El slug lo declara el propio ticket. Sin prefijo `cursor/`, sin sufijo aleatorio (ver [`../branch-naming.md`](../branch-naming.md)) |
| Rama de docs sueltos | `docs-<slug>` (opcional, W1 lo controla) |
| Rama de release | ninguna: `main` es la fuente; despliegue con `deploy.yml` |
| Merge | **squash** obligatorio; rama borrada al fusionar |
| Commits | Conventional Commits en inglés con scope de módulo: `feat(billing): issue invoice`, `fix(reconciler): ignore active job` |
| Autor commits | **La cuenta de GitHub real de quien hizo el trabajo** (`git config user.name` / `user.email` por repositorio; registro en [`../WORKSTREAMS.md`](../WORKSTREAMS.md) §3). No hay identidad compartida: «Equipo KoiCloud» es el nombre público del equipo, no un autor de git. `Co-authored-by:` solo cuando otro humano participó de verdad; **nunca** trailers de Cursor, Antigravity, Gemini o Claude |
| Tamaño de PR | ≤ 500 líneas netas (sin generados / lockfiles / fixtures) |
| Un PR = un ticket | Sin “mientras estaba ahí…” |

---

## 3. Árbol exacto del repositorio

```
koicloud/
├── AGENTS.md                            # FUENTE ÚNICA de reglas para agentes; Cursor y
│                                        #   Antigravity CLI la leen directo (≤ ~12 000 car.)
├── GEMINI.md                            # puntero para Antigravity / Gemini
├── CLAUDE.md                            # puntero para Claude Code
├── CONTRIBUTING.md                      # la versión corta, para humanos
├── .cursor/
│   └── rules/
│       ├── 00-harness.mdc               # always-on: re-ancla el arranque (Cursor ya lee AGENTS.md)
│       ├── 10-api.mdc                   # glob: apps/api/**
│       ├── 20-web.mdc                   # glob: apps/web/**
│       ├── 30-node-agent.mdc            # glob: apps/node-agent/**
│       ├── 40-cli-mcp.mdc               # glob: apps/cli/**, apps/api/app/mcp/**
│       └── visual.mdc                   # glob: apps/web/** — piel obligatoria (docs/visual-guidelines.md)
├── .agents/                             # Antigravity (workspace rules)
│   └── rules/
│       ├── 00-harness.md                # trigger: always_on — núcleo AUTOSUFICIENTE, no un
│       │                                #   puntero: el IDE no garantiza leer AGENTS.md
│       ├── 10-api.md · 20-web.md · 30-node-agent.md · 40-cli-mcp.md · visual.md
│       └──                              #   generados desde .cursor/rules con make sync-rules
├── .github/
│   ├── CODEOWNERS                       # handles reales de los cuatro
│   ├── PULL_REQUEST_TEMPLATE.md         # incluye check de autoría y de trailers
│   ├── review-prompt.md                 # prompt del revisor automático
│   ├── ISSUE_TEMPLATE/
│   │   ├── ticket.md
│   │   └── ccr.md                       # Contract Change Request
│   ├── scripts/
│   │   └── check_ownership.py           # falla si un PR toca rutas fuera de su workstream
│   └── workflows/
│       ├── ci.yml                       # ownership · api · web · node-agent · cli · secrets · rules · authorship
│       ├── ai-review.yml                # revisor bloqueante + auto-merge en rutas no críticas
│       └── deploy.yml                   # W4 con aprobación W1: SSH + docker compose up en VPS
├── Makefile                             # atajos: up · migrate · seed · check · check-<area> · contracts · sync-rules
├── docker-compose.yml                   # dev local: db, api, worker, node-agent(mock|docker), web
├── .env.example                         # placeholders documentados; nunca secretos reales
├── .gitignore
├── LICENSE                              # MIT (equipo confirma)
├── README.md                            # portada del repo (español); reenvía a docs/
├── docs/
│   ├── WORKSTREAMS.md                   # dueño, rutas, DoD y registro de identidades de git
│   ├── tickets/                         # de aquí sale "¿qué me toca?"
│   │   ├── README.md                    # convención: frontmatter, estados, las seis secciones
│   │   ├── W0-00-plantilla.md
│   │   ├── w1/ · w2/ · w3/ · w4/        # 00-INDEX.md + un archivo por ticket
│   │   └──                              #   W2-06-detalle-pond.md → rama w2-detalle-pond
│   ├── architecture/                    # copia (o enlace) del pack de este store
│   ├── visual-guidelines.md             # piel obligatoria de apps/web (fuente de visual.mdc)
│   ├── adr/                             # 001-*.md ADRs específicos que emerjan durante el semestre
│   ├── runbooks/                        # cómo restaurar backup, cómo rotar gate password, etc.
│   ├── manual-usuario/                  # W4 al final del semestre
│   ├── manual-tecnico.md
│   └── reporte-carga.md                 # W4 después de las pruebas k6
├── apps/
│   ├── api/
│   │   ├── pyproject.toml               # uv; deps fijadas en Fase 0
│   │   ├── uv.lock
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   │   └── versions/
│   │   │       ├── 0001_initial.py      # tablas mínimas de todos los módulos comprometidos
│   │   │       └── 0002_seed_plans.py   # sandbox · micro · pro
│   │   ├── app/
│   │   │   ├── main.py                  # crea FastAPI, monta routers, monta /mcp, handlers de error
│   │   │   ├── core/                    # config · errors · time · security · db · auth deps
│   │   │   ├── commands/                # reglas: create_pond · delete_pond · run_sql · subscribe · …
│   │   │   ├── modules/
│   │   │   │   ├── auth/                # W3
│   │   │   │   ├── users/               # W3
│   │   │   │   ├── billing/             # W3
│   │   │   │   ├── notifications/       # W3
│   │   │   │   ├── admin/               # W3
│   │   │   │   ├── ponds/               # W1
│   │   │   │   ├── jobs/                # W1
│   │   │   │   ├── nodes/               # W1
│   │   │   │   ├── backups/             # W1
│   │   │   │   ├── metering/            # W1
│   │   │   │   ├── agent_access/        # W1
│   │   │   │   └── sql_console/         # W4
│   │   │   ├── internal_api/            # W1: /internal/v1/* (jobs, heartbeat, samples)
│   │   │   ├── mcp/                     # W4: tools FastMCP montadas en /mcp
│   │   │   ├── workers/                 # W1: main.py, scheduler.py, reconciler.py
│   │   │   └── tooling/
│   │   │       └── export_openapi.py    # regenera packages/contracts/openapi.json
│   │   └── tests/                       # conftest.py + factories.py globales; tests por módulo dentro de modules/<m>/tests
│   ├── node-agent/                      # W1
│   │   ├── pyproject.toml
│   │   ├── uv.lock
│   │   └── agent/
│   │       ├── main.py                  # loop principal
│   │       ├── config.py
│   │       ├── client.py                # cliente httpx contra /internal/v1
│   │       ├── drivers/
│   │       │   ├── base.py              # ABC: create_pond, start, stop, delete, dump, restore, sample
│   │       │   ├── docker_driver.py
│   │       │   └── mock_driver.py       # obligatorio en CI; usa fallos inyectables MOCK_FAIL_NEXT=…
│   │       ├── handlers/                # un handler por tipo de job
│   │       │   ├── create_pond.py
│   │       │   ├── delete_pond.py
│   │       │   ├── start_pond.py
│   │       │   ├── stop_pond.py
│   │       │   ├── backup_pond.py
│   │       │   └── restore_pond.py
│   │       └── sampler.py               # muestreo periódico de tamaño/estado por pond
│   ├── web/                             # W2
│   │   ├── package.json
│   │   ├── pnpm-lock.yaml
│   │   ├── vite.config.ts
│   │   ├── tsconfig.json
│   │   ├── tailwind.config.ts
│   │   ├── postcss.config.js
│   │   ├── index.html
│   │   ├── public/
│   │   │   └── koi/koi-sheet.png        # sprite 32×32 · 8 cuadros de nado + 4 de giro (visual-guidelines §7.1)
│   │   └── src/
│   │       ├── main.tsx                 # importa las fuentes Fontsource (Fraunces · Instrument Sans · IBM Plex Mono)
│   │       ├── index.css                # tokens canónicos + puente shadcn (visual-guidelines §2); único lugar con hex literales
│   │       ├── app/                     # router · providers · layout · guards
│   │       ├── api/
│   │       │   ├── schema.d.ts          # generado con openapi-typescript, NO editar a mano
│   │       │   ├── client.ts            # openapi-fetch + interceptor refresh
│   │       │   └── hooks/               # TanStack Query, uno por feature
│   │       ├── features/                # landing · auth · dashboard · ponds · sql-console · billing · backups · account · admin · agent-access
│   │       ├── components/
│   │       │   ├── koi/                 # <Koi/> y <Pond size="hero|panel|inline"/> con prefers-reduced-motion
│   │       │   └── ui/                  # shadcn/ui — no editar salvo tema
│   │       ├── lib/                     # auth-store · format · errors (Problem→es) · constants
│   │       └── mocks/                   # MSW handlers a partir de examples del OpenAPI
│   └── cli/                             # W4
│       ├── pyproject.toml               # publicable con `pip install -e apps/cli`
│       ├── uv.lock
│       └── koicloud_cli/
│           ├── __init__.py
│           ├── main.py                  # Typer app
│           ├── config.py                # ~/.config/koicloud/config.json
│           ├── client.py                # httpx wrapper + confirm helpers
│           ├── commands/
│           │   ├── auth.py              # login · logout · whoami
│           │   ├── pond.py              # list · get · create · connection · delete
│           │   ├── sql.py               # run (read) · run --write (propose + confirm)
│           │   ├── subscription.py      # list · subscribe · cancel
│           │   ├── backup.py            # list · restore
│           │   ├── agent.py             # reveal · rotate
│           │   └── confirm.py           # koicloud confirm <token>
│           └── errors.py
├── packages/
│   └── contracts/
│       ├── openapi.json                 # generado por apps/api; commiteado
│       └── CHANGELOG.md                 # una línea por cambio de contrato aprobado
├── infra/                               # W4
│   ├── Caddyfile
│   ├── docker-compose.prod.yml
│   ├── koicloud-agent.service           # systemd
│   ├── scripts/
│   │   ├── bootstrap-vps.sh             # apt · docker · usuarios · directorios
│   │   ├── deploy.sh                    # se dispara desde deploy.yml
│   │   └── backup-internal-db.sh        # cron: dump diario de la base interna
│   └── env/
│       └── prod.env.example
├── load/                                # W4
│   └── k6/
│       ├── login.js
│       ├── list_ponds.js
│       └── create_pond.js
└── scripts/                             # W1
    ├── seed-dev.sh                      # crea usuario demo, contrata plan, crea pond mock
    ├── what-do-i-do.sh                  # nombre → workstream → siguiente ticket abierto
    ├── sync-rules.py                    # regenera .agents/rules desde .cursor/rules
    └── check-links.sh                   # revisa links relativos en docs/
```

**Por qué el árbol trae infraestructura de dos agentes.** Carlos trabaja en Cursor y los
otros tres en Antigravity, y las dos herramientas no leen los mismos archivos: Cursor lee
`AGENTS.md` y `.cursor/rules/`; Antigravity lee `.agents/rules/` y `GEMINI.md` (su CLI
además lee `AGENTS.md`). Por eso `AGENTS.md` es la fuente, los punteros son de unas líneas,
y las reglas de área existen por duplicado generadas desde un solo original. El razonamiento
completo y los supuestos a verificar están en [`agent-docs.md`](./agent-docs.md) §4; los
archivos terminados, en [`../repo-bootstrap/`](../repo-bootstrap/README.md).

---

## 4. Layout obligatorio de un módulo backend

```
apps/api/app/modules/<name>/
  __init__.py         # ÚNICA superficie pública: re-exporta lo que otros módulos pueden usar
  router.py           # APIRouter(prefix="/<recurso>"); funciones ≤ 30 líneas; sin SQL ni reglas
  schemas.py          # Pydantic v2; cada modelo con `example` en json_schema_extra
  models.py           # SQLAlchemy 2.0 (Mapped[…]); solo tablas del módulo
  service.py          # reglas locales; recibe AsyncSession; lanza AppError; no conoce HTTP
  repository.py       # opcional: consultas SQLAlchemy reutilizables
  tasks.py            # opcional: tareas periódicas registradas por workers/scheduler.py
  errors.py           # opcional: subclases de AppError con `code` del catálogo
  tests/
    test_service.py   # unitario; DB real en transacción revertida
    test_api.py       # httpx AsyncClient contra la app
```

**Un módulo NO tiene:** `utils.py` genérico, `helpers.py`, código muerto, funciones sin usar, ni imports desde el interior de otro módulo (solo desde su `__init__.py`).

**Import lint** (`import-linter`) fuerza el grafo:

- `router` → `service` → `repository` / `models`.
- `service` puede importar `core/*` y llamar a `commands/*` (nunca al revés).
- Módulos **no** se importan entre sí salvo por su `__init__.py`.

---

## 5. Layout obligatorio del frontend

```
apps/web/src/
  main.tsx                                            # imports de Fontsource (Fraunces · Instrument Sans · IBM Plex Mono)
  index.css                                           # tokens + puente shadcn (visual-guidelines §2)
  app/
    router.tsx · providers.tsx · layout/…              # shell, nav, guards
  api/
    schema.d.ts                                       # generado, NO editar
    client.ts                                         # openapi-fetch + interceptor refresh
    hooks/<feature>.ts                                # TanStack Query
  features/
    landing/ · auth/ · dashboard/
    ponds/pages/*.tsx  ponds/components/*.tsx  ponds/tabs/*.tsx
    sql-console/ · billing/ · backups/
    account/ · admin/ · agent-access/
  components/
    koi/…                                             # <Koi/> · <Pond/> (sprite en public/koi/)
    ui/…                                              # shadcn/ui; no editar a mano
  lib/
    auth-store.ts (Zustand) · format.ts · errors.ts · constants.ts
  mocks/
    browser.ts · handlers/<feature>.ts                # MSW; fixtures a partir de `example` del OpenAPI
```

**Reglas:**

- Página ≤ 250 líneas (si crece, se parte en componentes).
- Estado de servidor solo en TanStack Query. Estado de auth solo en `auth-store`.
- Nada de `fetch` directo fuera de `api/`.
- Nada de `any`.
- Textos en español en JSX (sin i18n; el proyecto es local).
- **Piel:** todo color, radio, espacio y duración sale de los tokens de `index.css`, definidos en [`../visual-guidelines.md`](../visual-guidelines.md) §2. Ningún hex literal en componentes, ninguna utilidad arbitraria (`bg-[#…]`), ningún `dark:` ni clase `.dark` — el tema es claro y único. `tailwind.config.ts` extiende `colors`, `spacing`, `borderRadius`, `boxShadow` y `fontSize` desde esas variables.
- La **arquitectura de información** de cada pantalla sale de [`../entrega-2/mockups/pantallas-principales.html`](../entrega-2/mockups/pantallas-principales.html) (campos, tablas, pasos); su tema oscuro no se copia.

---

## 6. Configuración y entornos

### 6.1 Variables (`.env.example`)

Cada variable con placeholder y un comentario que documente su significado. Ejemplos representativos (lista completa en el `.env.example` del repo cuando exista):

| Variable | Ambito | Descripción |
|----------|--------|-------------|
| `DATABASE_URL` | api, worker | `postgresql+asyncpg://koi:pass@db:5432/koi` |
| `JWT_SECRET` | api | 32 bytes aleatorios; nunca commiteado |
| `REFRESH_TTL_DAYS` | api | 30 |
| `POND_PASSWORD_KEY` | api, node-agent | clave Fernet para cifrar `db_password_encrypted` |
| `AGENT_MODE` | node-agent | `mock` (dev/CI) o `docker` (VPS) |
| `NODE_ID` / `NODE_TOKEN` | node-agent | id del nodo y secreto compartido con la API |
| `KOICLOUD_DOMAIN` | api, caddy | `koicloud.example` (placeholder hasta Fase 1) |
| `NODE_PUBLIC_HOST` | api | IP/hostname público del VPS para armar URIs |
| `POND_PORT_RANGE_START` / `_END` | api, node-agent | `15000` / `15999` |
| `MCP_ENABLED` | api | `true` en dev/prod, `false` si se quiere apagar solo el MCP |
| `EMAIL_PROVIDER` | api | `console` (dev/CI) o `resend` (prod) |
| `INVOICE_DIR` | api | `/var/lib/koicloud/invoices` |
| `BACKUP_DIR` | api, node-agent | `/var/lib/koicloud/backups` |

### 6.2 Configuración local (dev)

- `docker-compose.yml` levanta `db`, `api`, `worker`, `node-agent` (con `AGENT_MODE=mock` por defecto) y `web` (dev server con proxy).
- `make up` = `docker compose up -d` + `make migrate`.
- `make seed` corre `scripts/seed-dev.sh`: crea usuario `demo@koicloud.dev` / contraseña, contrata `micro`, crea un pond mock.
- Sin conexión al VPS, `AGENT_MODE=mock` simula contenedores en memoria (latencia configurable, fallos inyectables). Es el modo obligatorio en CI.

### 6.3 Configuración producción

- `infra/docker-compose.prod.yml` corre `db`, `api`, `worker`, `caddy` como servicios del compose.
- `node-agent` corre como servicio systemd (fuera del compose) para tener acceso limpio a `/var/run/docker.sock`.
- Caddy termina TLS con ACME, sirve la SPA estática desde `/srv/koicloud/web`, proxya `/api/*` y `/mcp` a `api:8000`, bloquea `/internal/*` para tráfico no loopback, expone `/openapi.json` y `/docs`.
- Backups internos: cron diario `infra/scripts/backup-internal-db.sh`; retención 7 días.

---

## 7. CI (esqueleto, sin implementar)

`.github/workflows/ci.yml` corre estos jobs en paralelo. Son *required* en la branch protection de `main`.

| Job | Qué corre | Falla si |
|-----|-----------|----------|
| `ownership` | `.github/scripts/check_ownership.py` (deriva el workstream del prefijo `wN-` de la rama y lo compara contra CODEOWNERS) | El PR toca rutas fuera del workstream de la rama (salvo etiqueta `cross-workstream`); en ramas `w1-` solo avisa |
| `api` | `uv sync --frozen`; `ruff check`; `ruff format --check`; `mypy`; `lint-imports`; `alembic upgrade head` en base efímera; `alembic heads == 1`; `pytest --cov`; `export_openapi` y `git diff --exit-code packages/contracts/openapi.json` | Cualquier paso |
| `web` | `pnpm install --frozen-lockfile`; `pnpm gen:api` y verifica que `schema.d.ts` no cambió; `pnpm lint`; `pnpm typecheck`; `pnpm test`; `pnpm build` | Cualquier paso |
| `node-agent` | ruff, mypy, pytest con `AGENT_MODE=mock` | Cualquier paso |
| `cli` | ruff, mypy, pytest | Cualquier paso |
| `secrets` | gitleaks contra el diff (y contra el historial en el primer PR) | Cualquier hallazgo no exceptuado en `.gitleaks.toml` (W1) |
| `rules` | `python3 scripts/sync-rules.py` y `git diff --exit-code .agents/rules/` | `.agents/rules/` no está al día respecto de `.cursor/rules/`, o alguna regla pasa de 12 000 caracteres (tope de Antigravity) |
| `authorship` | recorre `git log origin/main..HEAD`: autor de cada commit contra el registro de `docs/WORKSTREAMS.md` §3, y `grep -i 'co-authored-by.*\(cursor\|antigravity\|gemini\|claude\)\|generated with'` | Un commit trae un trailer de herramienta, o un autor que no está en el registro del equipo |

`.github/workflows/ai-review.yml` corre un revisor automático (Cursor Bugbot o Anthropic claude-code-action) con el prompt fijo de `.github/review-prompt.md`. El job **falla** si el veredicto es `KOI-REVIEW: REQUEST_CHANGES` o si no hay veredicto (§ 8 de [`agent-docs.md`](./agent-docs.md)).

`.github/workflows/deploy.yml` (W4) se dispara con push a `main` que toque `apps/**`, `packages/contracts/**` o `infra/**`. Hace `ssh <vps> "cd /srv/koicloud && infra/scripts/deploy.sh"`.

---

## 8. Ownership (CODEOWNERS)

El archivo terminado, listo para copiar, es
[`../repo-bootstrap/_github/CODEOWNERS`](../repo-bootstrap/_github/CODEOWNERS). No se
duplica aquí para que no existan dos versiones que se contradigan. Su forma:

| Zona | Dueño |
|---|---|
| Núcleo, comandos, migraciones, contratos, node-agent, `Makefile`, `docker-compose.yml`, `.env.example`, `scripts/**`, `.github/**` (excepto `deploy.yml`), el harness de agentes (`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `.cursor/**`, `.agents/**`), `docs/architecture/**`, `docs/tickets/**` | `@carloshugoeg` (W1) |
| `apps/web/**` | W2 |
| `apps/api/app/modules/{auth,users,billing,notifications,admin}/**` | W3 |
| `apps/api/app/modules/sql_console/**`, `apps/cli/**`, `infra/**`, `load/**`, manuales | W4 |
| `apps/api/app/mcp/**`, `infra/**`, `.github/workflows/deploy.yml` | W4 **y** W1 (doble aprobación) |
| Manifiestos de dependencias (`package.json`, `pnpm-lock.yaml`, `pyproject.toml`, `uv.lock`) | su workstream **y** W1 |

Reglas que sostienen esa tabla:

- Cualquier archivo **no listado** cae en W1.
- Los manifiestos de dependencias siempre exigen aprobación de W1 aunque los edite otro
  workstream: así se revisa cada dependencia nueva sin bloquear el trabajo.
- Las tools MCP son de W4 solo en sus archivos de lectura; el montaje, el gate y las tools
  mutantes son de W1, y por eso `apps/api/app/mcp/**` lleva doble dueño.
- Los handles de W2, W3 y W4 son `@Jasgu097`, `@Josh-JM` y `@diegojoachin07`. GitHub
  ignora en silencio una línea con un handle inexistente, y esa ruta queda sin dueño sin
  que nadie se entere. El registro de handles vive en
  [`../WORKSTREAMS.md`](../WORKSTREAMS.md) §1.

---

## 9. Bootstrap (documental, no ejecutable ahora)

Cuando el equipo decida crear el repo (Fase 0), estos son los pasos exactos. **No los ejecutes durante la fase de diseño.**

La lista operativa completa, con verificaciones y criterios de «hecho», está en
`internal/dual-agent-infra-handoff.md` del store. Resumen:

1. Crear el repo público `carloshugoeg/koicloud` desde `gh` (credenciales en `docs/github-publish.md` del store).
2. **Fijar la identidad de git antes del primer commit:** `git config user.name` / `user.email` con la cuenta real de quien bootstrapea (`../WORKSTREAMS.md` §3). Nada de identidad de equipo compartida, ningún trailer de herramienta.
3. Copiar el pack de [`../repo-bootstrap/`](../repo-bootstrap/README.md) a la raíz —`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `.cursor/rules/`, `.agents/rules/`, `.github/`, `docs/tickets/`, `scripts/`— y hacer el primer commit `chore: initial scaffold`.
4. Copiar/enlazar `docs/architecture/` desde este store como fuente única de arquitectura, `docs/workstreams.md` como `docs/WORKSTREAMS.md`, y `docs/visual-guidelines.md` + `docs/visual-guidelines-agent-prompt.md` como fuente única de apariencia (el segundo se instala además como `.cursor/rules/visual.mdc`, y se replica con `make sync-rules`).
5. Editar `.github/CODEOWNERS` y `docs/WORKSTREAMS.md` con los handles y correos reales de los cuatro. Sin esto, las rutas de W2/W3/W4 quedan sin dueño.
6. Configurar branch protection en `main`:
   - Require PR before merging; 1 approval; dismiss stale approvals on new commits.
   - Require review from Code Owners.
   - Required status checks: `ownership`, `api`, `web`, `node-agent`, `cli`, `secrets`, `rules`, `authorship`, `ai-review`.
   - Require linear history; allow squash only; allow auto-merge; block force-push and deletions.
7. Añadir secretos: `ANTHROPIC_API_KEY` (o el proveedor del revisor automático), `KOI_BOT_TOKEN` (PAT de la cuenta reviewer-bot), `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `POND_PASSWORD_KEY`, `JWT_SECRET`.
8. Correr el primer PR de prueba (creación de `apps/api/app/main.py` con “hello world”) para verificar CI, ownership, autoría y `ai-review` en verde.
9. **Probar el harness con una persona real:** alguien que no escribió el pack abre el repo en su herramienta y escribe «Soy Jason. ¿Qué me toca y ejecútalo?». Si no sale el ticket correcto con su rama y sus rutas prohibidas, el harness no está listo y se arregla antes de repartir trabajo.
10. A partir de aquí, seguir el plan de Fase 0 → Sprints en [`feature-breakdown.md`](./feature-breakdown.md).

---

## 10. Cambios al scaffolding

Cualquier cambio a este scaffolding (mover carpetas, crear apps nuevas, cambiar convenciones) pasa por **ADR** en `docs/adr/`. Los agentes no reorganizan carpetas por gusto; cualquier propuesta que empiece con “sería más limpio si…” se rechaza sin ADR.

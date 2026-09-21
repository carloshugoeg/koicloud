# Dependencias y stack

Elecciones de tecnología con *por qué* explícito, ancladas a lo que el Equipo KoiCloud ya conoce y a lo que el semestre puede sostener sin operar infraestructura de terceros. Las versiones exactas se fijan en Fase 0 (`uv.lock`, `pnpm-lock.yaml`) y se congelan hasta que un CCR las mueva.

Cualquier dependencia nueva se declara en el PR bajo “Dependencias nuevas” (o se rechaza).

---

## 1. Backend Python

| Área | Elección | Rol | Por qué esta y no otra |
|------|----------|-----|------------------------|
| Runtime | **Python 3.12** | Sostener API, worker, node-agent y CLI en una sola versión | Última versión estable con `asyncio` sólido; el equipo ya la usó en el curso previo |
| Gestor de deps | **uv** | Instala, resuelve y crea lockfiles reproducibles | Rápido y determinista; `uv sync --frozen` en CI garantiza build repetible |
| API HTTP | **FastAPI** + **Uvicorn** | Router, validación, OpenAPI automático | Genera OpenAPI + docs sin extra; async nativo se casa con asyncpg |
| Validación | **Pydantic v2** + **pydantic-settings** | Esquemas de request/response, config por env | Ya integrado con FastAPI; los `example` alimentan mocks del frontend |
| ORM y migraciones | **SQLAlchemy 2.0 async** + **Alembic** | Modelos con `Mapped[...]`, migraciones lineales | Standard de facto; el equipo conoce SQL crudo si hace falta bajarse del ORM |
| Driver Postgres | **asyncpg** | Conexiones async a la BD interna y a ponds | Tres a cinco veces más rápido que psycopg async; API estable |
| Concurrencia de jobs | **PostgreSQL `SELECT … FOR UPDATE SKIP LOCKED`** | Cola con `jobs` | No añade broker; suficiente para el aula |
| Locks periódicos | **`pg_advisory_lock`** | Un solo worker corre el reconciler/scheduler | Evita duplicar tareas si el worker escala accidentalmente |
| MCP | **FastMCP** (Python) | Server MCP montado en la misma app | Se integra con FastAPI sin proceso extra; si `n.n` da problemas, se corre como proceso aparte detrás de Caddy (plan B documentado) |
| Auth de usuario | **PyJWT** + **argon2-cffi** | JWT access + refresh; hash de passwords | Estables y bien mantenidas; argon2id es el algoritmo recomendado |
| Cifrado en reposo | **cryptography (Fernet)** | Cifra `db_password_encrypted` de cada pond | Simple, simétrico, suficiente para el semestre; la clave vive en `POND_PASSWORD_KEY` |
| Rate limiting | **slowapi** | Login, registro, forgot, gate MCP | Integra con FastAPI; contador en memoria basta en un solo nodo |
| Correo | **Resend** (prod) / consola (dev + CI) | Verificación, recuperación, aviso de suspensión | Free tier suficiente; en dev se imprimen a stdout |
| PDF de factura | **fpdf2** | Genera PDFs con IVA desglosado | Sin dependencias externas de Chromium/wkhtml; ejecuta en el mismo proceso |
| CLI | **Typer** + **httpx** + **rich** | Comandos y salida tabulada | Typer usa type hints como FastAPI; el equipo ya está acostumbrado |
| HTTP cliente | **httpx** | Node-agent y CLI hablan al control plane | Timeouts, retry, TLS estables; async y sync |
| Docker | **docker (SDK Python)** | Node-agent crea/borra contenedores | Estándar; equipo ya lo tocó en cursos previos |
| Lint/format | **ruff** (check + format) | Estilo unificado en Python | Rápido; un solo binario para lint + format |
| Type check | **mypy** | Estricto en `core/`, `commands/`, `billing/`, `reconciler/` | Se activa `strict` en núcleo; resto con `check_untyped_defs` |
| Arquitectura import | **import-linter** | Prohíbe importar módulos entre sí salvo por `__init__.py` | Automatiza la regla del layout |
| Tests | **pytest** + **pytest-asyncio** + **httpx** | Unit + API tests con DB real en transacción | Coverage ≥ 60 % en `billing` y `jobs`/`reconciler`; sin SQLite |

**Lo que NO se agrega al backend (registrado aquí para rechazar propuestas futuras):**

- **Django / Flask** — FastAPI cumple todo; cambiar rompe todo el stack.
- **Celery / RQ / Dramatiq** — la cola en PG es suficiente y una dependencia menos.
- **Kafka / RabbitMQ / Redis** — R-04 y R-02 lo prohíben.
- **SQLAlchemy sync** — mezclar sync y async duplica complejidad; nos quedamos en async.
- **Alembic autogenerate** — se usa migraciones escritas a mano; autogenerate es útil pero equivoca constraints y default values.
- **Sentry** — telemetría fuera de alcance; log a stdout.
- **Prometheus / Grafana** — sin status page pública, sin métrica externa.
- **OpenTelemetry** — mismo motivo.
- **OAuth server (Authlib, Ory)** — la seguridad completa de agentes es V2.

---

## 2. Frontend

| Área | Elección | Rol | Por qué |
|------|----------|-----|---------|
| Framework | **React 18+** + **TypeScript strict** | SPA de la Web | El equipo ya lo conoce; ecosistema abundante |
| Bundler | **Vite** | Dev server rápido + build | Menor overhead que Next.js para una SPA sin SSR |
| Estilos | **Tailwind CSS** | Utility-first sin CSS custom disperso | Rápido de escribir; combinable con shadcn/ui |
| Componentes | **shadcn/ui** | Componentes base copiables (no dependencia empaquetada) | Da control sobre el código, no ata a versiones remotas |
| Tipografía | **Fontsource**: `@fontsource-variable/fraunces`, `@fontsource/instrument-sans`, `@fontsource/ibm-plex-mono` | Las tres familias de la piel (display / UI / mono) | Autohospedadas: el VPS no depende del CDN de Google. Las familias las fija [`../visual-guidelines.md`](../visual-guidelines.md) §4 |
| Iconos | **lucide-react** | Un solo set, trazo 1.5 px | Set único y coherente; 16 px en línea, 20 px en botones (piel §9) |
| Toasts | **sonner** | Avisos no bloqueantes | Ligero, headless, se tematiza con los tokens (piel §6.5) |
| Router | **React Router v6** | Rutas cliente | Estándar; sin frameworks fullstack |
| Server state | **TanStack Query v5** | Cache + refetch de la API | Elimina spaghetti de useEffect + fetch |
| Local state | **Zustand** | Estado de auth y UI trivial | Sin boilerplate de Redux |
| Formularios | **react-hook-form** + **zod** | Validación de formularios | Rápido, sin re-render por tecla |
| Contratos API | **openapi-typescript** + **openapi-fetch** | Tipos generados desde OpenAPI + cliente HTTP | Fuente única: el backend es el que manda |
| Mocks | **MSW** | Handlers que devuelven los `example` del OpenAPI | Frontend arranca sin backend real |
| Editor SQL | **CodeMirror 6** (`@uiw/react-codemirror`, `@codemirror/lang-sql`) | Consola SQL con highlight y atajos | Ligero comparado con Monaco |
| Gráficos | **Recharts** | Vista de uso mensual | Componentes React puros |
| Tests | **Vitest** + **Testing Library** | Render + interacción | Rápido; compatible con Vite |
| Lint | **ESLint** + **Prettier** | Estilo unificado en TS | Estándar del ecosistema |
| Package manager | **pnpm** | Locking rápido y determinista | `--frozen-lockfile` en CI |

**No se agrega:**

- **Next.js / Remix** — no necesitamos SSR/RSC; el SPA basta.
- **Redux / Redux Toolkit** — Zustand + TanStack Query cubren estado.
- **Material UI / Chakra UI** — shadcn/ui + Tailwind es suficiente y más controlable.
- **Monaco Editor** — pesado; CodeMirror cubre.
- **i18n** — sin i18n; el proyecto es local, textos en español directos.
- **Storybook** — overhead sin ROI en un semestre.
- **`next-themes` o cualquier librería de modo oscuro** — el tema es claro y único ([`../visual-guidelines.md`](../visual-guidelines.md) §0).
- **Fuentes por CDN de Google, o `Inter`/`Roboto`/`Arial` como fuente de UI** — las tres familias son las de la piel, autohospedadas por Fontsource.
- **Otro set de iconos** (react-icons, heroicons, phosphor) o packs de ilustración vectorial — un solo set (`lucide`); la única ilustración es el pixel art del koi.
- **Librerías de animación** (Framer Motion, Lottie, GSAP) — el movimiento es CSS con `steps()` y duraciones de token; la interfaz de datos es casi inmóvil (piel §8).

---

## 3. Proxy, TLS y sistema

| Área | Elección | Por qué |
|------|----------|---------|
| Reverse proxy y TLS | **Caddy** | ACME automático; una sola config; `respond` para bloquear `/internal/*` de fuera |
| Contenedores | **Docker Engine** en Ubuntu 24.04 | Estándar; el equipo ya lo usa |
| systemd | Nativo del SO | El node-agent corre fuera del compose |
| Cron (backup interno) | Cron del SO | Para el respaldo diario de la propia BD interna |

---

## 4. Herramientas de desarrollo del equipo

| Área | Elección | Rol |
|------|----------|-----|
| Editor | **Cursor** (Ultra por semestre) | Editor + agente principal del equipo |
| Agentes de IA | Cursor Agent, Cursor Bugbot, opcional Claude Code | Ver [`agent-docs.md`](./agent-docs.md) para reglas y publicación |
| Diagramas | **Mermaid** (fuentes `.mmd`) | Se renderiza a SVG con `@mermaid-js/mermaid-cli` |
| Docs | Markdown | GitHub renderiza; los PDFs de entregas se generan con `pandoc` cuando aplique |

---

## 5. CI / CD

| Área | Elección | Rol |
|------|----------|-----|
| CI runner | **GitHub Actions** (runner hosted) | 6 jobs required + revisor automático |
| Revisor de IA | **Cursor Bugbot** (preferido) o **anthropic/claude-code-action** | Ver [`agent-docs.md`](./agent-docs.md) §Revisor |
| Secret scanning | **gitleaks** | Job `secrets` |
| Load testing | **k6** | 3 escenarios: login, list_ponds, create_pond |
| SSH deploy | Solo `ssh` + `docker compose` + `alembic upgrade` + rsync | Sin Ansible/Terraform |

---

## 6. Filosofía de pinning de versiones

- **Lockfiles obligatorios**: `uv.lock` para todo lo Python, `pnpm-lock.yaml` para la web. CI corre con `--frozen`; el `main` nunca cambia por resolución oportunista.
- **Bumps de versiones**: entran como PR aparte con etiqueta `chore(deps)`. Solo W1 los revisa (por CODEOWNERS de los lockfiles). Se preferirán bumps mensuales agrupados sobre bumps individuales.
- **Runtimes fijos**: Python 3.12.x, Node 20.x, Postgres 16.x. Cambios de major requieren ADR.
- **Imagen del pond**: `postgres:16-alpine`. Cambiar el tag es CCR (afecta a las URIs devueltas al cliente y a compatibilidad con `pg_dump` del agente).

---

## 7. Dependencias externas que no controlamos

| Externa | Uso | Qué asumimos |
|---------|-----|--------------|
| **Resend** (correo, prod) | Verificación y recuperación | Free tier; si falla, degradamos a consola y avisamos al usuario en la Web |
| **Anthropic API** (revisor CI + demo MCP) | Revisor automático + Claude Desktop en la demo | Free/paid; si el revisor Anthropic falla, se cambia a Bugbot o a revisión manual (con retraso) |
| **Let's Encrypt** (ACME por Caddy) | TLS del dominio | Estable; Caddy maneja renovación |
| **VPS provider** (por decidir) | Servidor único | Cualquier proveedor con Ubuntu 24.04, ≥4 GB RAM, IP pública, 20+ GB SSD |

Ninguna otra dependencia externa entra sin CCR.

---

## 8. Qué NO agregar (regla explícita para agentes)

Esta lista es la contra-cara del stack. Un PR que introduzca cualquiera de estas se rechaza (`REQUEST_CHANGES` sin discusión):

1. Otro framework backend (Django/Flask/Litestar/Starlette solo).
2. Otro framework frontend (Next.js/Remix/Angular/Vue).
3. Otro ORM (SQLModel/Peewee/Tortoise).
4. Otro sistema de cola (Celery/RQ/Redis).
5. Otro store (Redis/Memcached/DynamoDB/Mongo). La única base es Postgres.
6. Otro editor de código en la web (Monaco/AceEditor).
7. Otro sistema de contenedores (K8s, Docker Swarm, Nomad).
8. Otro sistema de secrets (Vault, AWS SSM). Los secretos viven en `.env` del VPS y en GitHub Secrets.
9. Otro sistema de observabilidad (Sentry, Prometheus, Grafana, OTel).
10. Cualquier librería de “agent framework” (LangChain, LlamaIndex, CrewAI). El servidor MCP se hace con FastMCP directo.
11. Cualquier cliente OAuth (Authlib, Ory, Auth0). La gate del MCP es password.
12. Cualquier ORM para el frontend (Prisma-like) o cliente “tipado” diferente a `openapi-fetch`.
13. Cualquier utilidad “de conveniencia” con más de 200 KB y menos de 3 usos previstos.
14. Cualquier pieza que pelee con la piel: librería de modo oscuro, otra familia tipográfica, otro set de iconos, packs de ilustración o motor de animación. La apariencia está cerrada en [`../visual-guidelines.md`](../visual-guidelines.md).

Si el agente cree que necesita algo de esta lista, la respuesta correcta es `BLOQUEADO: requiere CCR porque <razón>`.

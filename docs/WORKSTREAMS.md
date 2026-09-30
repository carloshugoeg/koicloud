# Workstreams de KoiCloud

Equipo KoiCloud son cuatro workstreams con dueño explícito. Cada uno es responsable de una
superficie del producto de punta a punta: la escribe, la prueba, la defiende en la
exposición y aparece como dueño en `CODEOWNERS`. Nadie «ayuda» en la zona de otro: si algo
de otra zona te bloquea, se pide por ticket o por CCR.

Este documento se copia al repositorio de implementación como `docs/WORKSTREAMS.md` y es lo
que un agente lee para saber de quién es cada archivo.

---

## 1. Mapa

| Workstream | Persona | GitHub | Superficie | Rama | Tickets |
|---|---|---|---|---|---|
| **W1** — Núcleo y data plane | Carlos Hugo Escobar | `@carloshugoeg` | API, modelo de datos, cola de jobs, node-agent, contratos, infraestructura | `w1-…` | `docs/tickets/w1/` |
| **W2** — Web | Jason Gutiérrez | `@Jasgu097` | La SPA completa: todas las pantallas que el usuario ve | `w2-…` | `docs/tickets/w2/` |
| **W3** — Cuentas y dinero | Jousé Menendez | `@Josh-JM` | Registro, sesión, perfil, planes, contratación, facturas, correos, administración | `w3-…` | `docs/tickets/w3/` |
| **W4** — Superficies y operación | Diego Joachin | `@diegojoachin07` | CLI, consola SQL, tools MCP de lectura, pruebas de carga, manuales, despliegue | `w4-…` | `docs/tickets/w4/` |

Los handles de la tabla son los de GitHub, verificados con `gh api users/<login>`.
`CODEOWNERS` usa los mismos: `@Jasgu097`, `@Josh-JM` y `@diegojoachin07`.

---

## 2. Directorios por dueño

| Workstream | Rutas propias |
|---|---|
| **W1** | `apps/api/app/{core,commands,internal_api,workers,tooling}/**` · `apps/api/app/main.py` · `apps/api/app/modules/{ponds,jobs,nodes,backups,metering,agent_access}/**` · `apps/api/alembic/**` · `apps/node-agent/**` · `packages/contracts/**` · `Makefile` · `docker-compose.yml` · `.env.example` · `scripts/**` · `AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `.cursor/**`, `.agents/**` · `.github/**` (excepto `deploy.yml`) · `docs/architecture/**`, `docs/adr/**`, `docs/runbooks/**` |
| **W2** | `apps/web/**` · `docs/tickets/w2/**` |
| **W3** | `apps/api/app/modules/{auth,users,billing,notifications,admin}/**` · `docs/tickets/w3/**` |
| **W4** | `apps/api/app/modules/sql_console/**` · `apps/api/app/mcp/**` (solo tools de lectura) · `apps/cli/**` · `infra/**` · `load/**` · `.github/workflows/deploy.yml` (con aprobación de W1) · `docs/manual-usuario/**`, `docs/manual-tecnico.md`, `docs/reporte-carga.md` · `docs/tickets/w4/**` |

**Cualquier archivo no listado pertenece a W1.** Una rama `w1-…` puede tocar cualquier ruta;
las demás fallan el job `ownership` de CI si tocan algo ajeno. Los manifiestos de
dependencias (`package.json`, `pnpm-lock.yaml`, `pyproject.toml`, `uv.lock`) los edita su
workstream, pero CODEOWNERS exige además la aprobación de W1: así se revisa cada dependencia
nueva sin bloquear el trabajo.

---

## 3. Identidad de git (cada quien firma lo suyo)

Cada commit se atribuye a la **cuenta de GitHub real de quien hizo el trabajo**. No hay una
identidad compartida: «Equipo KoiCloud» es el nombre público del equipo en el README, los
documentos de entrega y la interfaz, **no** un autor de git.

En cada máquina, dentro del repositorio:

```bash
git config user.name  "Nombre Apellido"
git config user.email "correo-de-tu-cuenta-de-github"
git config --get user.email    # verificá antes del primer commit
```

| Persona | `user.name` | `user.email` |
|---|---|---|
| Carlos Hugo Escobar | Carlos Hugo Escobar | `hescobar06cvo@gmail.com` (o su noreply de GitHub) |
| Jason Gutiérrez | Jason Gutiérrez | `124702997+Jasgu097@users.noreply.github.com` |
| Jousé Menendez | Jousé Menendez | `175631417+Josh-JM@users.noreply.github.com` · `josueandremj@gmail.com` |
| Diego Joachin | Diego Joachin | `175631462+diegojoachin07@users.noreply.github.com` · `diegojoachin26@gmail.com` |

Si preferís no publicar tu correo, usá el `noreply` de GitHub
(`ID+handle@users.noreply.github.com`, visible en *Settings → Emails*): cuenta igual para la
atribución y para el gráfico de contribuciones. Lo que **no** vale es firmar con el correo
de otra persona ni con una identidad genérica.

**Ningún commit lleva trailers de herramienta**: nada de `Co-authored-by: Cursor`,
`Co-authored-by: Antigravity`, `Co-authored-by: Gemini`, `Co-authored-by: Claude` ni líneas
del tipo «Generated with…». `Co-authored-by:` se usa solo cuando otro compañero humano
trabajó de verdad en ese commit.

---

## 4. Definition of Done por superficie

Lo común a todos: PR fusionado en `main` por squash, CI en verde, revisor automático en
`APPROVE`, criterios de aceptación del ticket verificados uno por uno en el PR, caso feliz
ejecutado a mano y descrito, y `make check-<área>` con la salida real pegada.

**W1 — Backend, node-agent e infraestructura.** Endpoint nuevo con prueba de API (caso feliz
y al menos un error del catálogo). Regla de negocio nueva con prueba unitaria contra base
real en transacción revertida. Migraciones lineales con una sola cabeza, verificado en CI.
OpenAPI regenerado con `make contracts` cuando el contrato cambia (siempre por CCR). Handler
del node-agent con prueba contra `mock_driver`. Cambios de infraestructura validados con
`docker compose config` y con su runbook actualizado.

**W2 — Web.** Página nueva con prueba de render del caso feliz y prueba de la interacción
principal. Todos los datos por hooks de TanStack Query. Sin `any`, sin warnings de ESLint,
`tsc --noEmit` limpio. Los tres estados del listado presentes: cargando, vacío y error.
Lista de verificación de piel de `docs/visual-guidelines.md` §11.2 marcada en el PR, y
captura del estado feliz adjunta. Usable a 360 px.

**W3 — Cuentas y dinero.** Prueba de API por endpoint, cubriendo el error del catálogo que
el ticket nombra. Textos de correo y de error en español, revisados. Nada de lógica de
cálculo en el router: el comando calcula, el router transporta. Si falta un campo, hay un
CCR enlazado en el PR.

**W4 — Superficies y operación.** Comando de CLI con prueba usando `httpx.MockTransport` y
`--help` actualizado. Tool MCP de ≤ 25 líneas con prueba in-process. Toda mutación documenta
en el PR su ruta `propose → confirm` completa. Documentos y manuales con la evidencia real
que citan (salida de k6, capturas de la Web terminada).

---

## 5. Los tickets del sprint

**Viven en el repositorio, en `docs/tickets/<wN>/`.** Un archivo por ticket, con el estado en
su frontmatter y las seis secciones obligatorias. La convención completa está en
`docs/tickets/README.md`, y el plan de cada workstream en `docs/tickets/<wN>/00-INDEX.md`.

Para saber qué sigue sin leer el directorio a mano:

```bash
bash scripts/what-do-i-do.sh Jason
```

GitHub Issues y el tablero del proyecto siguen siendo la vista pública del avance; el archivo
del repositorio es la fuente que leen los agentes, y el issue enlaza a él.

---

## 6. Reglas transversales

1. **Un PR = un ticket ≤ 500 líneas netas** (sin generados, lockfiles ni fixtures). Si no
   cabe, el ticket se parte antes de escribir código.
2. **Los contratos están congelados:** rutas y schemas del OpenAPI, códigos de error, firmas
   de `app/commands/*`, tablas y enums. Solo cambian con un **CCR** aprobado por W1
   (plantilla `.github/ISSUE_TEMPLATE/ccr.md`).
3. **Revisión cruzada:** todo PR necesita CI en verde, el veredicto del revisor automático y,
   en rutas críticas, la aprobación del dueño por CODEOWNERS.
4. **Si estás bloqueado más de 24 horas, se escala el mismo día.** Nadie pasa un fin de
   semana atascado en silencio.
5. **Cada quien defiende lo suyo.** Antes de abrir un PR tenés que poder explicar, sin leer,
   qué hace tu código y por qué así: la exposición final evalúa eso.

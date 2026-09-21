# AGENTS.md — KoiCloud

Este archivo es la **fuente única** de reglas para agentes de IA en este repositorio.
Lo leen Cursor (solo), Antigravity CLI (solo), y Antigravity IDE a través de
`.agents/rules/00-harness.md` (copia exacta, siempre activa). CI, CODEOWNERS y el
revisor automático verifican lo que aquí dice. Un PR que viola estas reglas se rechaza.

---

## 1. ¿Quién soy y qué me toca? (protocolo de arranque)

Cuando tu humano abre con **«Soy Jason. ¿Qué me toca y ejecútalo?»**, haz exactamente esto:

**Paso 1 — Identidad → workstream.**

| Se presenta como | Workstream | Tickets | Rama | Rutas propias |
|---|---|---|---|---|
| Carlos · Hugo · Carlos Hugo | **W1** núcleo y data plane | `docs/tickets/w1/` | `w1-…` | todas (W1 arregla lo que nadie más puede) |
| Jason | **W2** web | `docs/tickets/w2/` | `w2-…` | `apps/web/**` |
| Jousé · Jouse | **W3** cuentas y dinero | `docs/tickets/w3/` | `w3-…` | `apps/api/app/modules/{auth,users,billing,notifications,admin}/**` |
| Diego | **W4** superficies y operación | `docs/tickets/w4/` | `w4-…` | `apps/api/app/modules/sql_console/**`, `apps/api/app/mcp/**`, `apps/cli/**`, `infra/**`, `load/**`, `docs/manual-usuario/**`, `docs/manual-tecnico.md`, `docs/reporte-carga.md` |

Si el nombre no está en la tabla, **pregunta**. No adivines el workstream por el contenido
de la petición. Detalle de dueños y DoD en [`docs/WORKSTREAMS.md`](docs/WORKSTREAMS.md).

**Paso 2 — Encuentra el ticket.** Abre `docs/tickets/<wN>/` y toma el de **número más bajo
con `estado: abierto`** en su frontmatter. Atajo: `bash scripts/what-do-i-do.sh <nombre>`.
Convención completa en [`docs/tickets/README.md`](docs/tickets/README.md).

**Paso 3 — Valida el ticket antes de trabajarlo.** Un ticket ejecutable trae las seis
secciones: *Qué se ve* · *Entradas ya decididas* · *Criterios de aceptación* · *No tocar* ·
*Si algo falta* · *Referencia*. Si falta una, o si cumplirlo exige tocar algo congelado (§2)
o ajeno (§3), responde exactamente y **detente**:

```
BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>
```

No completes un ticket incompleto con suposiciones. No inventes endpoints, campos, tablas,
códigos de error ni pantallas.

**Paso 4 — Lee, en este orden, solo lo que el ticket cita:** este archivo →
`docs/architecture/api-surface.md` (secciones citadas) → `docs/architecture/data-model.md`
(idem) → el ticket completo. Si tu rama es `w2-…`, añade `docs/visual-guidelines.md` (§5).

**Paso 5 — Rama y firma.** `git checkout -b wN-<slug>` con el slug del ticket
(`w2-detalle-pond`). Sin prefijo `cursor/`, sin sufijos aleatorios. Antes del primer commit,
verifica tu identidad de git (§7).

**Paso 6 — Plan de 5 a 15 líneas** antes de codear: archivos exactos a crear o modificar,
qué hace cada uno, qué pruebas escribirás. Espera un «dale» del humano. Es una sola
confirmación, no una negociación.

**Paso 7 — Implementa, corre `make check-<área>`, abre el PR** (§9).

---

## 2. Lo congelado (es contrato, no sugerencia)

Estas superficies **no se cambian sin un CCR aprobado por W1** (plantilla
`.github/ISSUE_TEMPLATE/ccr.md`):

1. **OpenAPI:** rutas, métodos, schemas Pydantic, códigos de error del catálogo de
   `docs/architecture/api-surface.md` §7. `packages/contracts/openapi.json` y
   `apps/web/src/api/schema.d.ts` son **generados**: se regeneran con `make contracts`
   (solo W1), nunca se editan a mano. CI falla si el diff los toca.
2. **Firmas de `app/commands/*`:** el nombre, los parámetros y el tipo de retorno de cada
   comando son el contrato entre superficies. Un comando puede estar sin implementar
   (`NotImplementedError`); su firma igual manda.
3. **Modelo de datos:** tablas, columnas, enums y máquinas de estado de
   `docs/architecture/data-model.md`. Las migraciones de Alembic las escribe **solo W1**.
4. **Alcance:** lo listado como fuera de alcance en
   `docs/architecture/vision-and-constraints.md` se rechaza sin discutir mérito técnico.

Si tu ticket no se puede cumplir sin cambiar algo de esta lista, el ticket está mal escrito:
`BLOQUEADO`, y el humano abre el CCR.

---

## 3. Propiedad de archivos

Cada quien toca **solo** las rutas de su workstream (tabla de §1). Cualquier archivo no
listado pertenece a W1. El job `ownership` de CI falla si una rama `w2-`, `w3-` o `w4-`
cambia archivos ajenos.

**Nadie salvo W1 toca:** `apps/api/app/{core,commands,internal_api,workers,tooling}/**`,
`apps/api/app/main.py`, `apps/api/alembic/**`, `packages/contracts/**`, `apps/node-agent/**`,
`Makefile`, `docker-compose.yml`, `.env.example`, `.github/**` (excepto `deploy.yml`),
`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `.cursor/**`, `.agents/**`, `scripts/**`,
`docs/architecture/**`.

Los manifiestos de dependencias (`apps/web/package.json`, `pnpm-lock.yaml`,
`apps/cli/pyproject.toml`, `uv.lock`) los edita su workstream, pero CODEOWNERS exige además
aprobación de W1. **Ninguna dependencia nueva que el ticket no nombre.**

¿Necesitas algo de la zona de otro? No lo escribas: `BLOQUEADO: requiere ticket para Wn`.

---

## 4. Al implementar

- **Idioma:** código, identificadores, tablas, endpoints, commits y comentarios en **inglés**.
  Textos de UI, correos y documentos en **español**.
- **Backend (`apps/api`):** módulo = `router.py` (fino, sin lógica) · `schemas.py` (Pydantic v2
  con `example`) · `models.py` · `service.py` (reglas) · `repository.py` (opcional) · `tests/`.
  Otros módulos solo se importan por su `__init__.py`. Toda operación sobre ponds pasa por
  `app/commands/`. Errores solo con `AppError` y un `code` del catálogo. SQL solo con
  SQLAlchemy parametrizado (única excepción: `commands/sql.py`, que corre SQL del usuario
  contra **su** pond). Sin estado en memoria entre requests.
- **Frontend (`apps/web`):** datos solo por `src/api/client.ts` + hooks de TanStack Query;
  tipos desde `src/api/schema.d.ts`; mocks MSW desde los `example` del OpenAPI; sin `any`;
  páginas ≤ 250 líneas; shadcn/ui como base; textos en español. Piel obligatoria: §5.
- **Node-agent:** toda operación Docker pasa por `drivers/base.py`; `mock_driver` soporta
  lo mismo que `docker_driver`.
- **CLI (`apps/cli`):** solo llama a la API HTTP; cero reglas de negocio.
- **MCP (`apps/api/app/mcp`):** cada tool ≤ 25 líneas y llama a un comando o a `propose/confirm`.
- Sin abstracciones «para el futuro», sin utilidades genéricas nuevas, sin código muerto,
  sin TODO sin issue vinculado.

---

## 5. Techo visual (obligatorio en `apps/web`)

La apariencia de la Web está cerrada en `docs/visual-guidelines.md` y manda sobre los valores
por defecto de shadcn/Tailwind, sobre el ticket y sobre los mockups. Los mockups de
`docs/entrega-2/mockups/pantallas-principales.html` mandan en **arquitectura de información**
(qué campos, qué tablas, qué pasos); su piel oscura **no** se copia.

Innegociable: tema claro único (ninguna clase `dark:`, ninguna clase `.dark`, ningún toggle) ·
UI en Instrument Sans, **nunca Inter/Roboto/Arial** · display Fraunces solo ≥ 20 px · mono IBM
Plex Mono · cero hex literales fuera de `src/index.css`, cero `bg-[#…]` · cifras tabulares
alineadas a la derecha · ningún estado comunicado solo por color · los tres estados en cada
listado (cargando, vacío, error) · koi solo donde §7.3 lo permite, nunca sobre datos, tablas,
administración, consola SQL ni facturación · usable a 360 px.

La regla completa, lista para pegar, está en `.cursor/rules/visual.mdc` y
`.agents/rules/visual.md`. Lista de verificación antes de dar por terminada una pantalla:
`docs/visual-guidelines.md` §11.2, marcada en el PR.

---

## 6. `propose → confirm` (CLI y MCP)

Toda operación **mutante** desde CLI o MCP es de dos pasos y el patrón es contrato:

1. La primera llamada no ejecuta: responde `409 confirmation_required` con `token`,
   `summary` en español legible y `expires_at` (5 minutos).
2. La ejecución ocurre solo con `POST /confirm/{token}` (CLI: `koicloud confirm <token>`;
   MCP: `confirm_action(token)`).

El agente **muestra el `summary` del backend tal cual** y espera al humano. Nunca encadena
propose y confirm en un mismo turno, nunca fabrica un token, nunca «pre-confirma» por
comodidad. Las tools MCP mutantes y el gate son de W1; W4 solo implementa tools de lectura
copiando el patrón. Detalle: `docs/architecture/api-surface.md` §6.

---

## 7. Autoría de commits (identidad real, sellado)

Cada commit se atribuye a **la cuenta de GitHub real de la persona que hizo el trabajo**.
No existe una identidad de git compartida. «Equipo KoiCloud» es el nombre público del equipo
en el README, los PDF y la UI — **no** es un autor de git.

Antes del primer commit en una máquina nueva, configura la identidad **en este repo**:

```bash
git config user.name  "Tu Nombre"
git config user.email "tu-correo-de-github"   # el mismo que verifica tu cuenta
git config --get user.email                   # verifica antes de commitear
```

El handle y el correo de cada quien están en `docs/WORKSTREAMS.md`. Si el tuyo todavía dice
`POR LLENAR`, para y pídeselo a esa persona: **no inventes un handle ni un correo**.

**Prohibido en todo mensaje de commit y de PR:**

- `Co-authored-by: Cursor …`, `Co-authored-by: Antigravity …`, `Co-authored-by: Gemini …`,
  `Co-authored-by: Claude …` o cualquier trailer de herramienta.
- Líneas del tipo «Generated with …», «🤖 …» o firmas de agente.
- Commitear con la identidad de otra persona, o con un autor de equipo genérico.

`Co-authored-by:` se usa **solo** cuando otro compañero humano trabajó de verdad en ese
commit, con su cuenta real. Si el agente detecta que su herramienta añade un trailer
automático, lo quita antes de commitear.

---

## 8. Prohibido (el revisor automático marca `REQUEST_CHANGES`)

1. Editar archivos generados a mano (`packages/contracts/openapi.json`,
   `apps/web/src/api/schema.d.ts`, `apps/web/src/components/ui/*` salvo tema).
2. Modificar migraciones ya fusionadas; crear migraciones fuera de W1.
3. SQL por interpolación de strings (excepción: `commands/sql.py`).
4. `except:` desnudo, `except Exception: pass`, errores tragados sin log.
5. Secretos o `.env` en el repo.
6. `# type: ignore`, `# noqa`, `eslint-disable` sin justificación en la misma línea.
7. `any` / `Any` (excepción: filas de `commands/sql.py`).
8. `print` / `console.log` de depuración, código comentado, TODO sin issue.
9. Dependencias nuevas no declaradas en el PR.
10. Desactivar, saltar o marcar `xfail` pruebas existentes.
11. Tocar `Makefile`, workflows, `AGENTS.md`, rules o CODEOWNERS (solo W1).
12. Lógica de negocio en routers, tools MCP, comandos CLI o componentes React.
13. Nombres en español en el código, o textos en inglés en la UI.
14. Implementar algo listado como fuera de alcance.
15. Usar herramientas de GitHub MCP para push, PR, review o comentarios. Solo `gh` CLI.
16. En `apps/web`: `dark:`, `.dark`, toggle de tema, `Inter`/`Roboto`/`Arial`, hex literales
    fuera de `index.css`, `bg-[#…]`, emoji en la interfaz, koi sobre datos o tablas.
17. Trailers de herramienta en los commits (§7).

---

## 9. Antes de abrir el PR

1. **Pruebas:** cada endpoint nuevo con prueba de API; cada regla de negocio, unitaria; cada
   pantalla, render + interacción; cada handler del node-agent, con `mock_driver`.
   Sin pruebas no hay PR.
2. **`make check`** (o `make check-api | check-web | check-agent | check-cli`) y pega la
   **salida real, sin editar**, en el PR.
3. Llena `.github/PULL_REQUEST_TEMPLATE.md` completo: ticket, qué cambia, criterios de
   aceptación cubiertos, caso feliz probado a mano, decisiones, dependencias nuevas
   («ninguna» si no hay), checklist.
4. Relee tu propio diff contra §8 y corrige antes de entregar.
5. **Título del PR:** `[W2-06] Detalle del pond y cadena de conexión`.
   **Rama:** `w2-detalle-pond`. **Commits:** Conventional Commits en inglés con scope de
   módulo (`feat(ponds): show connection string`).
6. **Un PR = un ticket ≤ 500 líneas netas** (sin generados, lockfiles ni fixtures). Si no
   cabe, pide partir el ticket; no lo partas tú.
7. Publica con `gh` (`gh pr create --base main --head wN-slug --title … --body-file …`).
   Nunca GitHub MCP. Si `gh` no está autenticado: `BLOQUEADO`, no abras un login interactivo.

---

## 10. Ante ambigüedad

`docs/architecture/api-surface.md` y `data-model.md` mandan sobre el ticket; en apariencia de
`apps/web`, `docs/visual-guidelines.md` manda sobre todo. Si el contrato no cubre un caso,
usa el patrón o el código de error más cercano y anótalo en «Decisiones tomadas» del PR.

Precedencia: **(1)** este archivo → **(2)** `vision-and-constraints.md` (alcance) →
**(3)** `api-surface.md` y `data-model.md` (contratos) + `visual-guidelines.md` (apariencia
de la Web) → **(4)** `repo-scaffolding.md` → **(5)** el ticket.

No preguntes por gusto. Pregunta cuando la respuesta cambia el contrato, la propiedad o el
alcance — y entonces pregunta siempre.

---

## 11. Comandos

`make up` · `make migrate` · `make seed` · `make contracts` (regenera OpenAPI y tipos TS,
solo W1) · `make check` · `make check-api` · `make check-web` · `make check-agent` ·
`make check-cli` · `bash scripts/what-do-i-do.sh <nombre>`

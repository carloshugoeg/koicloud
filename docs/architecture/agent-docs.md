# Reglas para agentes de IA en el repo KoiCloud

Este documento define **cómo trabajan los agentes** dentro del futuro repo de implementación, con **dos herramientas en uso a la vez**: Carlos trabaja en Cursor; Jason, Jousé y Diego en Antigravity. Es la justificación y el índice de lo que se copia al repo; los archivos terminados —`AGENTS.md`, `GEMINI.md`, `.cursor/rules/`, `.agents/rules/`, `CODEOWNERS`, plantillas y `docs/tickets/`— viven listos para copiar en [`../repo-bootstrap/`](../repo-bootstrap/README.md).

Todo lo que aquí dice “obligatorio” se aplica por CI, por CODEOWNERS o por revisión humana; lo que no se puede automatizar, se aplica en revisión.

---

## 1. Principios que ningún agente relaja

1. **Un agente = un ticket = un workstream = un PR ≤ 500 líneas netas.** Si un ticket no cabe, se parte.
2. **La regla de propiedad manda.** Ningún agente toca archivos fuera de su workstream salvo que el ticket lo diga explícitamente y CODEOWNERS lo permita.
3. **Los contratos están congelados.** Rutas HTTP, tablas, enums y firmas de comandos solo cambian por CCR (Contract Change Request) aprobado por W1.
4. **Sin dependencias furtivas.** Cualquier paquete nuevo se declara en el PR o se rechaza.
5. **`gh` CLI, nunca GitHub MCP.** Publicación con `GH_TOKEN` (fine-grained) o Mac worker según `../github-publish.md`. Ver §7 aquí.
6. **Cada quien firma lo suyo.** Todo commit va con la cuenta de GitHub real de la persona que hizo el trabajo. No existe una identidad de git compartida: «Equipo KoiCloud» es el nombre público del equipo, no un autor. Trailers de Cursor, Antigravity, Gemini o Claude, jamás. Ver §7.
7. **Alcance sellado.** Todo lo listado como “fuera de alcance” en `docs/architecture/vision-and-constraints.md` se rechaza sin discutir mérito técnico.
8. **El trabajo se descubre desde el repo, no desde una conversación.** Un agente contesta «¿qué me toca?» leyendo `AGENTS.md` §1 y `docs/tickets/`, sin que nadie le explique el proyecto. Si eso deja de ser cierto, el harness está roto.

---

## 2. Quién es dueño de qué (recordatorio)

Detalle en [`repo-scaffolding.md`](./repo-scaffolding.md) §8 y en [`../workstreams.md`](../workstreams.md). Aquí solo la lectura para agentes:

| Workstream | Persona | Herramienta | Prefijo de rama | Rutas que puede tocar |
|------------|---------|-------------|------------------|-----------------------|
| **W1 — Núcleo & data plane** | Carlos | Cursor | `w1-…` | `apps/api/app/{core,commands,internal_api,workers,tooling,main.py,modules/{ponds,jobs,nodes,backups,metering,agent_access}}`, `apps/api/alembic`, `apps/node-agent`, `packages/contracts`, `docker-compose.yml`, `Makefile`, `.env.example`, `AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `.cursor/**`, `.agents/**`, `.github/**` (excepto `deploy.yml`), `scripts/**`, `docs/architecture/**`, `docs/adr/**`, `docs/runbooks/**`, `docs/tickets/**` |
| **W2 — Web** | Jason | Antigravity | `w2-…` | `apps/web/**` |
| **W3 — Cuentas y dinero** | Jousé | Antigravity | `w3-…` | `apps/api/app/modules/{auth,users,billing,notifications,admin}` |
| **W4 — Superficies y operación** | Diego | Antigravity | `w4-…` | `apps/api/app/modules/sql_console`, `apps/api/app/mcp`, `apps/cli`, `infra/**`, `load/**`, `.github/workflows/deploy.yml` (con aprobación W1), `docs/manual-usuario/**`, `docs/manual-tecnico.md`, `docs/reporte-carga.md` |

Cualquier archivo **no listado** es propiedad implícita de W1. Ramas `w1-` pueden tocar cualquier ruta (W1 arregla lo que nadie más puede); las demás fallan CI si tocan ajenos.

**Nombres de rama:** `wN-<slug>` en kebab-case (`w2-detalle-pond`), sin prefijo `cursor/` y sin sufijo aleatorio — convención en [`../branch-naming.md`](../branch-naming.md); el slug lo declara el propio ticket, así que el agente no lo inventa. El job `ownership` de CI deriva el workstream del prefijo `wN-` del nombre de la rama.

---

## 3. `AGENTS.md` — la fuente única

En el repo, **`AGENTS.md` en la raíz es el único documento autoritativo para agentes**. No se
duplica aquí: el archivo terminado, listo para copiar, es
[`../repo-bootstrap/AGENTS.md`](../repo-bootstrap/AGENTS.md). Este documento explica por qué
dice lo que dice; aquel es el que se lee en tiempo de trabajo.

Las siete preguntas que `AGENTS.md` tiene que contestar sin que nadie las explique:

| Pregunta | Dónde la contesta | Por qué está |
|---|---|---|
| **¿Quién soy?** | §1, tabla nombre → workstream → tickets → rama → rutas | El agente arranca con «Soy Jason», no con un prefijo de rama: la rama todavía no existe en el primer turno |
| **¿Dónde está mi trabajo?** | §1, pasos 2–3: ticket de número más bajo con `estado: abierto` en `docs/tickets/<wN>/` | El trabajo se descubre del repo, no de una conversación que nadie más ve |
| **¿Qué no puedo tocar?** | §3, propiedad de rutas, y la sección «No tocar» de cada ticket | Es la regla que más se rompe y la que CI verifica |
| **¿Cómo corro las pruebas?** | §9 y §11: `make check-<área>` con la salida real pegada en el PR | Sin evidencia real, el revisor no puede distinguir «pasa» de «dice que pasa» |
| **¿Cuál es el patrón de confirmación?** | §6: `propose → confirm` con `409 confirmation_required`, `summary` y token de 5 min | Es la mitad de la nota de la demo y la única superficie donde un error destruye datos |
| **¿Cuál es el techo visual de W2?** | §5, con el detalle en `docs/visual-guidelines.md` y la regla `visual` | Sin esto, cada pantalla inventa su propia paleta |
| **¿Con qué identidad firmo?** | §7: la cuenta real de GitHub de cada quien, sin trailers de herramienta | Ver §7 de este documento |

Y las dos respuestas que tiene que saber dar cuando algo no cuadra:

- **`BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>`** — si al ticket le falta
  una de sus seis secciones, o si cumplirlo exige tocar algo congelado o ajeno. El agente se
  detiene ahí: no completa el ticket con suposiciones y **no pasa al siguiente por su cuenta**.
- **«No hay ningún ticket abierto»** — si el directorio de su workstream no tiene ninguno.
  No hay trabajo sin ticket, porque sin criterios de aceptación no hay PR que pueda pasar.

**Tamaño:** `AGENTS.md` está en ~13 000 caracteres y ahí se queda. Cada sección nueva se
paga en contexto en **todas** las conversaciones de los cuatro, así que lo que se pueda
mover a una regla de área (`.cursor/rules/`, `.agents/rules/`) o a un documento que el
ticket cite, se mueve. El tope duro de 12 000 caracteres no aplica a este archivo sino a
cada regla de Antigravity (§4), y lo verifica `scripts/sync-rules.py` en CI.

---

## 4. Dos herramientas, un solo harness

Carlos trabaja en Cursor y los otros tres en Antigravity. Cada herramienta lee archivos
distintos, así que el mismo contenido viaja por dos caminos que no se contradicen.

| Archivo | Cursor | Antigravity IDE | Antigravity CLI | Claude Code |
|---|---|---|---|---|
| `AGENTS.md` (raíz) | lo lee completo, solo | **no garantizado** | lo lee | vía `CLAUDE.md` |
| `GEMINI.md` (raíz) | — | sí | sí | — |
| `CLAUDE.md` (raíz) | — | — | — | sí |
| `.cursor/rules/*.mdc` | sí (always-on y glob) | — | — | — |
| `.agents/rules/*.md` | — | **sí** (always-on, glob, manual, model decision) | sí | — |

De ahí salen cuatro decisiones:

1. **`AGENTS.md` es la fuente; `GEMINI.md` y `CLAUDE.md` son punteros de unas líneas.**
   Nunca copias parciales que se desincronicen.
2. **`.agents/rules/00-harness.md` es *always on* y autosuficiente**, no un puntero. Como no
   está garantizado que el IDE lea `AGENTS.md`, esa regla repite el núcleo: identidad,
   ticket, propiedad, congelado, autoría, `propose → confirm` y prohibiciones. Es la única
   duplicación deliberada del harness, y existe porque la alternativa es un agente que
   trabaja sin reglas.
3. **`.cursor/rules/00-harness.mdc` sí es corta**, porque Cursor ya lee `AGENTS.md` entero:
   solo re-ancla el protocolo de arranque en conversaciones largas.
4. **Las reglas de área (`10-api`, `20-web`, `30-node-agent`, `40-cli-mcp`, `visual`) son el
   mismo texto en los dos directorios**, y solo cambia el frontmatter:
   `globs` + `alwaysApply` en Cursor, `trigger: glob` + `globs` en Antigravity. Se edita la
   versión de Cursor y se regenera la otra con `python3 scripts/sync-rules.py`
   (`make sync-rules`); CI falla si el resultado no está commiteado. El script también
   verifica el tope de 12 000 caracteres por regla.

**Tres supuestos que se verifican el día del bootstrap** (están en la lista de
`internal/dual-agent-infra-handoff.md`), porque dependen de la versión instalada:

- Que Antigravity reconozca el frontmatter `trigger:` de `.agents/rules/`. Si no, la
  activación se fija a mano una sola vez desde *Customizations → Rules*: `00-harness` en
  *Always On* y las demás en *Glob*.
- Que acepte varios globs separados por coma en una misma regla (`40-cli-mcp`). Si no, se
  parte en dos archivos.
- Que el IDE, además, lea `AGENTS.md`. Si lo hace, `00-harness.md` es redundante pero
  inofensivo, y se queda.

**Lo que no se delega a la herramienta:** el prompt de arranque
(«Soy {nombre}. ¿Qué me toca y ejecútalo?») y el protocolo que dispara son idénticos en las
dos. Un compañero que cambie de herramienta no tiene nada nuevo que aprender. El paso a paso
para cada persona está en [`../agent-onboarding.md`](../agent-onboarding.md).

---

## 5. Harness boundaries (qué el harness cubre y qué no)

**Lo que el harness cubre (automatizado):**

- Ownership por `check_ownership.py` en CI, derivando el workstream del prefijo `wN-` de la rama.
- Contract check por `git diff --exit-code packages/contracts/openapi.json`.
- Tests, lint, format y typecheck de las cuatro apps.
- Prohibiciones de §8 buscadas por el revisor automático (patrones en el diff, no en el runtime).
- Espejo de reglas: `scripts/sync-rules.py` en CI verifica que `.agents/rules/` esté al día respecto de `.cursor/rules/` y dentro del tope de 12 000 caracteres.
- **Autoría:** un job de CI recorre los commits del PR y falla si encuentra un trailer de herramienta (`Co-authored-by: Cursor|Antigravity|Gemini|Claude`, «Generated with…») o un autor que no esté en la lista de cuentas del equipo. Lo que **no** puede verificar es que la persona correcta haya hecho el trabajo: eso se sostiene con que cada quien configure su `user.email` y lo defienda en la exposición.

**Lo que el harness NO cubre (queda en revisión humana):**

- Que un router llame al comando correcto (revisor lo puede señalar si el nombre difiere del ticket, pero no lo prueba).
- Que una regla de negocio esté “completa” (esas son las pruebas del ticket).
- Que la UX sea razonable — la revisión visual de W2 la hace un humano, con la lista de [`../visual-guidelines.md`](../visual-guidelines.md) §11.2 en la mano. El grep de `dark:`, `Inter` y `bg-[#` sí se puede automatizar; “esta pantalla se siente impresa y densa” no.
- Que el guion de la demo funcione — se ensaya, no se prueba con CI.

Los agentes no deben simular que lo no-cubierto está cubierto. Si un ticket requiere validación humana, se anota en el PR (“requiere revisión visual de W2”).

---

## 6. Definition of Done — por superficie

Cada superficie tiene un DoD ligeramente distinto según lo que el ticket pueda “probar solo”.

### 6.1 Backend (`apps/api`)

- Endpoint nuevo con **prueba de API** en `modules/<m>/tests/test_api.py` cubriendo caso feliz + al menos un error del catálogo.
- Regla de negocio nueva con **prueba unitaria** en `modules/<m>/tests/test_service.py` con DB real en transacción.
- Migración: solo W1. Migraciones lineales; una sola cabeza (`alembic heads` verificado en CI).
- OpenAPI regenerado si el contrato cambió (siempre vía CCR).
- Sin nuevas advertencias de ruff/mypy/import-linter.
- Caso feliz corrido a mano con `docker compose up` + `curl` documentado en el PR.

### 6.2 Frontend (`apps/web`)

- Página nueva con **test de render** (Vitest + Testing Library) que valide el estado feliz.
- **Test de interacción** para el flujo principal (click en “Crear pond” dispara request, muestra resultado).
- Todos los datos vienen por hooks de TanStack Query desde `api/hooks/`.
- Sin `any`; sin warnings de ESLint; typecheck limpio (`tsc --noEmit`).
- **Lista de verificación de piel** de [`../visual-guidelines.md`](../visual-guidelines.md) §11.2 marcada en el PR: sin `dark:`, sin `Inter`, sin hex literales, cifras tabulares, foco visible, estado nunca solo por color, los tres estados de datos (cargando / vacío / error), usable a 360 px.
- Screenshots del estado feliz en el PR (adjunto).

### 6.3 Node-agent (`apps/node-agent`)

- Handler nuevo con prueba usando `mock_driver` (fallos inyectables `MOCK_FAIL_NEXT=<action>`).
- Si toca `docker_driver`, prueba manual documentada en el PR con salida de `docker ps`.
- El `mock_driver` **debe** replicar la nueva capacidad; si no cabe en mock, se detiene y abre CCR (rompería CI).

### 6.4 CLI (`apps/cli`)

- Comando nuevo con prueba que use httpx `MockTransport`.
- Ayuda (`--help`) actualizada.
- Si es mutación, incluye la ruta `propose → confirm` documentada en el PR.

### 6.5 MCP (`apps/api/app/mcp`)

- Tool nueva ≤ 25 líneas.
- Prueba unitaria de la tool con la app FastAPI in-process (sin lanzar un proceso MCP real).
- Si es mutación, cita `confirm_action(token)` y muestra el `summary` de vuelta al chat.

### 6.6 Infra (`infra/**`)

- Cambio validado con `docker compose -f infra/docker-compose.prod.yml config` local.
- Runbook actualizado en `docs/runbooks/` si el cambio altera cómo se opera algo.
- Si toca `deploy.yml`, aprobación de W1 (CODEOWNERS) además de la del bot.

---

## 7. Autoría y publicación con `gh` (sin GitHub MCP)

### 7.1 Identidad: cada quien firma lo suyo

**Regla sellada:** cada commit se atribuye a la **cuenta de GitHub real de la persona que
hizo el trabajo**. No hay identidad de git compartida. «Equipo KoiCloud» es el nombre público
del equipo —README, PDF de entrega, interfaz— y **no** es un autor de git.

La identidad se fija **por repositorio**, no global, para que nadie firme con la cuenta
equivocada al saltar entre proyectos:

```bash
git config user.name  "Nombre Apellido"
git config user.email "correo-de-su-cuenta-de-github"   # o su noreply de GitHub
git config --get user.email      # verificar antes del primer commit
```

El registro de handles y correos está en [`../workstreams.md`](../workstreams.md) §3.
Usá exactamente esos valores: **nadie inventa un handle ni un correo
ajeno**, porque un commit mal atribuido es peor que uno sin atribuir — le asigna trabajo a
quien no lo hizo justo en el semestre en que se evalúa la contribución individual.

**Prohibido en todo mensaje de commit:** `Co-authored-by: Cursor|Antigravity|Gemini|Claude`,
líneas «Generated with …», emojis de firma de agente y cualquier trailer que la herramienta
agregue sola. El agente los quita antes de commitear; CI los rechaza si se le escapan.
`Co-authored-by:` se reserva para cuando otro compañero **humano** trabajó de verdad en ese
commit, con su cuenta real.

Por qué el cambio: la atribución compartida borraba la evidencia de quién hizo qué, que es
justo lo que la exposición final evalúa, y dejaba el historial de los cuatro en una sola
cuenta sin contribuciones individuales visibles.

### 7.2 Publicación

**Regla dura:** ningún agente llama a herramientas de GitHub MCP para push, PR o comentarios.
Todo pasa por `gh` con `GH_TOKEN` fine-grained (documentado en `../github-publish.md`).

```bash
# 1. Confirmar quién firma (debe salir tu correo, no el de otro)
git config --get user.name && git config --get user.email

# 2. Verificar credenciales
test -n "${GH_TOKEN:-}" && echo "GH_TOKEN ok" || echo "usar Mac worker"
gh auth status

# 3. Commit convencional, sin trailers de herramienta
git add -A
git commit -m "feat(billing): issue invoice on subscribe"

# 4. Revisar que el historial quedó limpio antes de publicar
git log --format='%an <%ae>' origin/main..HEAD | sort -u
git log origin/main..HEAD | grep -i 'co-authored-by\|generated with'   # sin resultados

# 5. Push y PR
git push -u origin w3-factura-pdf
gh pr create \
  --base main \
  --head w3-factura-pdf \
  --title "[W3-09] Factura PDF con IVA desglosado" \
  --body-file .github/pr-body.md
```

**Comentarios y reviews** también con `gh pr comment` / `gh pr review`. Nunca `mcp_github_*`.

Si `gh` falla por auth, el agente detiene el push y reporta:

> BLOQUEADO: `gh` no autenticado en este runner; usar Mac worker o rotar `GH_TOKEN`.

Nunca inicia un flujo interactivo de `gh auth login` en runners cloud (rompería la sesión).

---

## 8. Revisor automático (compuerta bloqueante)

`.github/workflows/ai-review.yml` corre en cada PR. Preferencia:

1. **Cursor Bugbot** si está disponible en el account/team → integración nativa, comentario con veredicto.
2. Alternativa: `anthropics/claude-code-action@v1` con el prompt de `.github/review-prompt.md`.

**Contrato del veredicto (obligatorio):** el revisor termina su comentario con una línea:

```
KOI-REVIEW: APPROVE
```

o

```
KOI-REVIEW: REQUEST_CHANGES
```

El job **falla** si no encuentra esa línea. Con `APPROVE` en rutas no críticas, la cuenta `koi-reviewer-bot` (PAT en secreto `KOI_BOT_TOKEN`) aprueba y activa auto-merge. En rutas críticas (`core/`, `commands/`, `alembic/`, `packages/contracts/`, `internal_api/`, `workers/`, `node-agent/`, `.github/**`, `AGENTS.md`, rules) se exige además la aprobación humana de W1 vía CODEOWNERS.

**Lo que el revisor marca `REQUEST_CHANGES` sin discusión**, además de las prohibiciones de
`AGENTS.md` §8: un commit con trailer de herramienta (`Co-authored-by: Cursor|Antigravity|
Gemini|Claude`, «Generated with…»), un autor que no esté en el registro de
`docs/WORKSTREAMS.md` §3, un PR sin la salida real de `make check`, y un PR que toca rutas
de otro workstream sin CCR ni etiqueta `cross-workstream`.

**El revisor NO sustituye:**

- El caso feliz manual (que sigue en el DoD del ticket).
- La revisión visual del W2 dueño de la SPA.
- El ensayo de la demo (§`risks-and-demo-plan.md` §Fallback MCP).

---

## 9. Contract Change Request (CCR)

Único mecanismo para cambiar algo congelado (rutas, tablas, enums, firmas de comandos, dependencias no listadas en `dependencies.md`).

1. Quien lo necesita abre un issue con la plantilla `ccr.md`: qué cambia, por qué el ticket no se puede cumplir sin cambio, impacto en otros workstreams, propuesta exacta (diff de `api-surface.md` / `data-model.md`).
2. W1 responde: aprobado / aprobado con cambios / rechazado con alternativa.
3. Si es aprobado, el dueño del módulo (o W1 si toca migraciones) hace el PR de contrato: actualiza `api-surface.md` / `data-model.md`, el schema/endpoint/migración, regenera `openapi.json` y `schema.d.ts`, añade línea a `packages/contracts/CHANGELOG.md`.
4. Los tickets afectados se actualizan.

**CCR exprés** (campo opcional nuevo, código de error nuevo, plantilla de correo nueva): mismo issue; W1 aprueba con comentario; el dueño del módulo hace el PR. Sin migraciones nunca es exprés.

---

## 10. Escalación

- **Bloqueo técnico > 24 h:** el agente escala al humano dueño del workstream. El humano decide: `BLOQUEADO`, `CCR` o alternativa.
- **Conflicto entre reglas:** el orden de precedencia es (1) `AGENTS.md`, (2) `docs/architecture/*`, (3) el ticket. Nunca al revés.
- **Sospecha de scope creep:** el agente responde `BLOQUEADO: parece fuera de alcance (…). Requiere CCR.`. Nunca implementa por si acaso.
- **Fallo repetido del revisor automático:** el humano dueño del workstream anota en el PR y pide revisión manual. No se “re-runna” hasta pasar de casualidad.

---

## 11. Fuentes de verdad (jerarquía)

Cuando dos documentos discrepan, este es el orden:

1. `AGENTS.md` (raíz del repo).
2. `docs/architecture/vision-and-constraints.md` (alcance).
3. `docs/architecture/api-surface.md` y `docs/architecture/data-model.md` (contratos).
4. `docs/architecture/repo-scaffolding.md` (organización) y `docs/architecture/dependencies.md` (stack).
5. `docs/architecture/interconnections.md` y `feature-breakdown.md` (coreografía y roadmap).
6. Ticket individual.

**Excepción por materia, no por rango:** en **apariencia** de `apps/web` (color, tipografía, espaciado, radios, movimiento, marca) manda [`../visual-guidelines.md`](../visual-guidelines.md) sobre cualquier documento de esta lista y sobre los mockups de la Entrega 2. Esos mockups siguen mandando en **arquitectura de información** (qué campos, qué tablas, qué pasos). Si un ticket pide una apariencia distinta, la respuesta es `BLOQUEADO`, no una excepción local.

Un cambio a un documento superior invalida cualquier ticket en curso que lo contradiga; el ticket se re-escribe o se aplaza.

---
trigger: always_on
description: Núcleo de reglas de KoiCloud — identidad, ticket, propiedad, contratos, autoría
---

# KoiCloud — reglas núcleo (siempre activas)

**Lee `AGENTS.md` en la raíz antes de escribir código.** Este archivo es un resumen
autosuficiente porque las reglas de Antigravity están limitadas a 12 000 caracteres;
`AGENTS.md` es la versión completa y manda si algo aquí queda corto.

## Arranque: «Soy {nombre}. ¿Qué me toca y ejecútalo?»

1. **Identidad → workstream:**

| Se presenta como | Workstream | Tickets | Rama | Rutas propias |
|---|---|---|---|---|
| Carlos · Hugo | W1 núcleo | `docs/tickets/w1/` | `w1-…` | todas |
| Jason | W2 web | `docs/tickets/w2/` | `w2-…` | `apps/web/**` |
| Jousé | W3 cuentas y dinero | `docs/tickets/w3/` | `w3-…` | `apps/api/app/modules/{auth,users,billing,notifications,admin}/**` |
| Diego | W4 superficies y operación | `docs/tickets/w4/` | `w4-…` | `apps/api/app/modules/{sql_console,mcp}/**`, `apps/cli/**`, `infra/**`, `load/**`, manuales |

Nombre que no esté en la tabla: **pregunta**, no adivines.

2. **Ticket:** el de número más bajo con `estado: abierto` en `docs/tickets/<wN>/`.
   Atajo: `bash scripts/what-do-i-do.sh <nombre>`. Convención: `docs/tickets/README.md`.
3. **Valida el ticket:** debe traer las seis secciones (*Qué se ve*, *Entradas ya decididas*,
   *Criterios de aceptación*, *No tocar*, *Si algo falta*, *Referencia*). Si falta una, o si
   cumplirlo exige tocar algo congelado o ajeno, responde y **detente**:
   `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>`.
4. **Lee solo lo citado:** `AGENTS.md` → `docs/architecture/api-surface.md` (secciones del
   ticket) → `docs/architecture/data-model.md` → el ticket. En `w2-…` añade
   `docs/visual-guidelines.md`.
5. **Rama:** `git checkout -b wN-<slug>` (`w2-detalle-pond`). Sin prefijo `cursor/`,
   sin sufijos aleatorios.
6. **Plan de 5–15 líneas** (archivos exactos, qué hace cada uno, qué pruebas) y espera un
   «dale». Una sola confirmación, no una negociación.
7. **Implementa → `make check-<área>` → PR** con la plantilla llena.

## Congelado (solo cambia con CCR aprobado por W1)

Rutas y schemas del OpenAPI y códigos de error del catálogo · firmas de `app/commands/*`
(la firma manda aunque el cuerpo sea `NotImplementedError`) · tablas, columnas, enums y
máquinas de estado · el alcance de `docs/architecture/vision-and-constraints.md`.
`packages/contracts/openapi.json` y `apps/web/src/api/schema.d.ts` son generados: se
regeneran con `make contracts` (solo W1) y nunca se editan a mano.

## Propiedad

Tocas **solo** las rutas de tu workstream. Todo lo no listado es de W1: `app/{core,commands,
internal_api,workers,tooling}/**`, `app/main.py`, `alembic/**`, `packages/contracts/**`,
`apps/node-agent/**`, `Makefile`, `docker-compose.yml`, `.env.example`, `.github/**`,
`AGENTS.md`, `.cursor/**`, `.agents/**`, `scripts/**`, `docs/architecture/**`.
CI (`ownership`) falla si una rama `w2-`, `w3-` o `w4-` toca ajenos. Ninguna dependencia
nueva que el ticket no nombre.

## Autoría de commits

Cada commit va con la **cuenta de GitHub real** de la persona que hizo el trabajo:

```bash
git config user.name "Tu Nombre" && git config user.email "tu-correo-de-github"
```

Handles y correos en `docs/WORKSTREAMS.md`; si el tuyo dice `POR LLENAR`, pídelo — no lo
inventes. **Nunca** añadas `Co-authored-by: Antigravity/Gemini/Cursor/Claude`, «Generated
with…» ni firmas de agente; si tu herramienta los agrega, quítalos antes de commitear.
«Equipo KoiCloud» es el nombre público del equipo, **no** una identidad de git.

## `propose → confirm` (CLI y MCP)

Toda mutación desde CLI o MCP es de dos pasos: la primera llamada responde
`409 confirmation_required` con `token`, `summary` y `expires_at` (5 min); la ejecución solo
ocurre con `POST /confirm/{token}`. Muestra el `summary` del backend tal cual y espera al
humano. Nunca encadenes propose y confirm en el mismo turno; nunca fabriques un token.

## Prohibido

Editar generados a mano · migraciones fuera de W1 · SQL por interpolación (excepto
`commands/sql.py`) · `except:` desnudo o errores tragados · secretos en el repo ·
`type: ignore` / `noqa` / `eslint-disable` sin justificación · `any` / `Any` · `print` y
`console.log` de depuración · TODO sin issue · dependencias no declaradas · desactivar o
`xfail` pruebas existentes · lógica de negocio en routers, tools MCP, comandos CLI o
componentes React · español en el código o inglés en la UI · implementar algo fuera de
alcance · GitHub MCP para push/PR/review (solo `gh` CLI) · trailers de herramienta.

## Antes del PR

Pruebas para todo lo nuevo · `make check-<área>` con la **salida real pegada** ·
plantilla de PR completa · título `[W2-06] Detalle del pond` · rama `w2-detalle-pond` ·
Conventional Commits en inglés · un PR = un ticket ≤ 500 líneas netas.

## Ambigüedad

Precedencia: `AGENTS.md` → `vision-and-constraints.md` → `api-surface.md` / `data-model.md`
(+ `visual-guidelines.md` para la apariencia de la Web) → `repo-scaffolding.md` → el ticket.
No inventes endpoints, campos, tablas, códigos ni pantallas. Pregunta cuando la respuesta
cambie el contrato, la propiedad o el alcance.

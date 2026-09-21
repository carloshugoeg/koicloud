# GEMINI.md

Este repositorio usa **`AGENTS.md` (raíz) como fuente única** de reglas para agentes.
Ábrelo y léelo completo antes de tocar cualquier archivo. Todo lo que necesitas —quién eres,
qué ticket te toca, qué no puedes tocar, cómo se firma un commit— está ahí.

Antigravity CLI lee este archivo y `AGENTS.md` directamente. Antigravity IDE además carga
las reglas de `.agents/rules/`: `00-harness.md` (siempre activa, resumen autosuficiente) y
las de área por glob. Si en tu versión del IDE las reglas no aparecen activas, ábrelas desde
el panel **Customizations → Rules** y fija la activación a mano: `00-harness` en *Always On*,
las demás en *Glob* con el patrón que declara cada archivo.

Arranque para tu humano: **«Soy {nombre}. ¿Qué me toca y ejecútalo?»** → el protocolo está en
`AGENTS.md` §1.

Orden de lectura para un ticket: `AGENTS.md` → `docs/architecture/api-surface.md` (solo las
secciones que el ticket cita) → `docs/architecture/data-model.md` (idem) → el ticket en
`docs/tickets/<wN>/`. Si trabajas en `apps/web/**`, añade `docs/visual-guidelines.md`.

Dos cosas que este archivo repite porque son las que más se rompen:

- **No añadas trailers de herramienta a los commits.** Nada de `Co-authored-by: Gemini`,
  `Co-authored-by: Antigravity`, «Generated with…» ni firmas de agente. Cada commit va con la
  cuenta de GitHub real de la persona (`AGENTS.md` §7).
- **No cambies nada congelado** (OpenAPI, firmas de `app/commands/*`, tablas, enums) sin un
  CCR aprobado. Si el ticket lo exige, responde `BLOQUEADO: …` y detente.

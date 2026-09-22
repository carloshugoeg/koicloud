# KoiCloud — Pack de arquitectura (implementación)

**Proyecto:** KoiCloud (DBaaS académico, PostgreSQL en Docker)
**Curso:** Ingeniería de Software I · Universidad Rafael Landívar · 2026
**Equipo KoiCloud:** Hugo Escobar · Jason Gutiérrez · Jousé Menendez · Diego Joachin
**Audiencia de este pack:** el propio equipo y los agentes que colaborarán en el repositorio de implementación.
**Estado:** planificación / diseño — **no** contiene código de aplicación, no crea repositorios, no despliega nada.

---

## Qué es este pack

Esta carpeta es el puente entre la **Entrega 2** (requisitos + diseño preliminar, sellados en [`../entrega-2/`](../entrega-2/)) y el repositorio de implementación que todavía no existe (nombre sugerido: `koicloud`). Congela las decisiones necesarias para que cuatro personas — con asistencia intensiva de Cursor Ultra — construyan el sistema sin pisarse, sin salirse del **alcance sellado** y sin fantasear con productos que no vamos a entregar.

El alcance sellado es el que aparece en [`../entrega-2/alcance.md`](../entrega-2/alcance.md): Web + CLI + MCP como adaptadores delgados sobre una sola API de control plane, PostgreSQL real en Docker, auth completa, billing simulado, consola SQL, respaldos, medición, admin, doble confirmación en mutaciones CLI/MCP, gate mínima de agente y guion de demo con fallback. Todo lo que aparece como “fuera de alcance” allí también está fuera aquí.

---

## Orden de lectura

Lee en este orden si nunca has visto el pack; luego usa cualquier documento como referencia suelta.

| # | Documento | Para qué sirve |
|---|-----------|----------------|
| 1 | [`vision-and-constraints.md`](./vision-and-constraints.md) | Problema, alcance sellado, no-goals, restricciones del semestre, qué “deslumbra” en la demo (MCP) sin mentir |
| 2 | [`system-architecture.md`](./system-architecture.md) | Control plane / data plane, tres superficies → una API, topología de despliegue, límites de confianza |
| 3 | [`interconnections.md`](./interconnections.md) | Flujos concretos: crear pond en Web, mutar+confirmar en CLI/MCP, ciclo job/queue, node-agent, respaldos, medición |
| 4 | [`data-model.md`](./data-model.md) | ER refinado, tablas, estados, estrategia de migraciones |
| 5 | [`api-surface.md`](./api-surface.md) | Recursos REST del control plane, patrón `propose → confirm token`, mapa CLI y MCP → mismos comandos |
| 6 | [`repo-scaffolding.md`](./repo-scaffolding.md) | Estructura exacta del monorepo, convenciones de config y entornos, esqueleto de CI |
| 7 | [`dependencies.md`](./dependencies.md) | Elecciones de stack con *por qué*, dependencias externas, qué **no** agregar |
| 8 | [`feature-breakdown.md`](./feature-breakdown.md) | Lista completa de funcionalidades → épicas → slices, dependencias y orden sugerido de construcción (camino a MVP para la demo) |
| 9 | [`agent-docs.md`](./agent-docs.md) | Reglas de trabajo con Cursor y otros agentes: quién posee qué, `AGENTS.md`, límites del harness, DoD por superficie, política de publicación (`gh` + autoría Equipo KoiCloud, sin GitHub MCP) |
| 10 | [`risks-and-demo-plan.md`](./risks-and-demo-plan.md) | Modos de falla, fallback si el LLM se cae en vivo, qué recortar si el semestre se atrasa |
| — | [`diagrams/`](./diagrams/) | Fuentes Mermaid opcionales de los diagramas embebidos en los otros documentos |
| — | [`../visual-guidelines.md`](../visual-guidelines.md) | **Piel del producto web**: color, tipografía, espaciado, movimiento, marca. Normativo para apariencia en `apps/web/**` |

**Regla de dos fuentes para la Web:** **piel = [`visual-guidelines.md`](../visual-guidelines.md); IA de pantallas = [`entrega-2/mockups/pantallas-principales.html`](../entrega-2/mockups/pantallas-principales.html)** (qué campos, qué tablas, qué pasos) + [`feature-breakdown.md`](./feature-breakdown.md). El tema oscuro de esos mockups quedó superado como apariencia; su estructura sigue vigente. Bloque listo para pegar en un agente de Cursor: [`../visual-guidelines-agent-prompt.md`](../visual-guidelines-agent-prompt.md).

Un [`internal/architecture-design-handoff.md`](../../internal/architecture-design-handoff.md) resume el pack en formato máquina para agentes que lleguen después.

---

## Cómo usar este pack en la implementación

1. **Copia el pack** (o enlázalo) al repo de implementación cuando se cree. La versión en el store es la de referencia mientras el repo no exista; a partir de allí conviven ambas hasta la primera copia y luego el repo manda.
2. **No lo edites al vuelo**: cambios de fondo pasan por CCR (Contract Change Request) como se describe en [`agent-docs.md`](./agent-docs.md). Correcciones tipográficas o de enlaces sí son PR directo.
3. **Los agentes** deben leer `vision-and-constraints.md` + `agent-docs.md` + su sección de `feature-breakdown.md` **antes** de escribir código. La regla es de `AGENTS.md`, no una sugerencia.
4. **Un ticket = un PR** dentro del workstream que lo posee. La propiedad de rutas está en [`repo-scaffolding.md`](./repo-scaffolding.md) §Ownership y en [`agent-docs.md`](./agent-docs.md).

---

## Diferencias contra la Entrega 2

La Entrega 2 diseña el **producto** (qué se le entrega al cliente/catedrático). Este pack diseña la **plataforma técnica** que lo produce:

- La Entrega 2 aprueba el *qué* (auth, ponds, billing, consola, backups, CLI/MCP thin, gate, confirm, demo). Aquí no lo re-litigamos.
- Este pack añade el *cómo del código*: repo layout, capas dentro de la API, patrón de comandos, contrato `propose → confirm`, ciclo de vida del job, harness de agentes.
- Los diagramas de la Entrega 2 se reutilizan; aquí solo añadimos los que aclaran mecanismos internos (queue, layers, límites de confianza, mapa de módulos).

---

## Diferencias contra el harness previo (`internal/harness/`)

El harness previo (`internal/harness/koicloud-harness/`) fue construido cuando el alcance incluía auto-curación como producto, status page pública, panel de flota, sandbox público, seguridad completa de agentes (OAuth 2.1, spend caps, aprobaciones), etc. **Ese alcance ya no está sellado.** Reutilizamos el patrón de organización (monorepo, cuatro workstreams, ownership por CODEOWNERS, revisor automático) pero:

- Se **quita** `sandbox` público sin registro, `status_page`, `fleet`, `agent budget/approvals` como sistema, `metrics streaming` en vivo, `auto-heal` como promesa, `cost explorer` avanzado.
- Se **mantiene** un reconciler mínimo (best-effort, no vendido) que corrige jobs zombis y `desired ≠ observed` cuando el operador lo pide, sin prometer SLA de auto-curación.
- Se **degrada** `agent_access` a la gate mínima de aula (URL + password revelable en el panel + `pending_confirmations`).
- Se **preserva** el patrón de tres capas (`router` fino → `commands` con reglas → `modules` con SQL), la cola en PostgreSQL con `SKIP LOCKED`, y el driver `mock | docker` del node-agent.
- Se **anula** su sección de diseño visual (`docs/workstreams/W2-web.md` §R4): pedía `Inter`, `#0F6E6E`, `#F26B1D` y modo oscuro por clase `dark`. La piel vigente es [`../visual-guidelines.md`](../visual-guidelines.md) — tema claro único, sin `dark:`, sin toggle de tema.

En resumen: **el harness previo es fuente de inspiración de patrones, no fuente de alcance.** Cuando este pack y el harness discrepen en qué se construye, este pack manda; en cómo se ve la Web, manda [`../visual-guidelines.md`](../visual-guidelines.md).

---

## Marca y tono

- **Team-facing:** todo doc se dirige al **Equipo KoiCloud**. Nunca “Carlos hace X en solitario”, nunca “integrante ejecutor”, nunca voz de un solo dueño.
- **Documentación de estudiante:** español; identificadores en inglés (`create_pond`, `pending_confirmations`); UI en español.
- **Apariencia de la Web:** la fija [`../visual-guidelines.md`](../visual-guidelines.md) — papel hueso, tinta casi negra, turquesa estructural, koi en pixel art como única ilustración, alma de reporte anual. Ningún documento de este pack redefine color ni tipografía.
- **Sin adornos:** los diagramas explican; las tablas resumen. Ningún adjetivo comercial (“plataforma agéntica”, “auto-curación garantizada”).
- **Sin GitHub MCP:** publicación con `gh` CLI y `GH_TOKEN` (ver `../github-publish.md`); autoría `Equipo KoiCloud`.

---

## Estado y próximos pasos (planificación)

Este pack se considera **completo para la etapa de diseño**. Los pasos siguientes, en orden:

1. Revisar el pack en la próxima reunión del equipo; anotar objeciones como issues de discusión (no editar el pack sin acuerdo).
2. Crear el repo de implementación `koicloud` (nombre sugerido, cambiable por acuerdo del equipo). Ver [`repo-scaffolding.md`](./repo-scaffolding.md) §Bootstrap.
3. Copiar `AGENTS.md`, `.cursor/rules/`, `.github/` según [`agent-docs.md`](./agent-docs.md).
4. Ejecutar la Fase 0 descrita en [`feature-breakdown.md`](./feature-breakdown.md) §Fase 0 antes de repartir tickets.

Cualquier cambio de fondo posterior se registra como **ADR** en el propio repo de implementación (`docs/adr/NNN-*.md`), no aquí.

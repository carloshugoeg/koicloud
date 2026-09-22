# Entrega 2 — Requisitos y diseño preliminar

**Proyecto:** KoiCloud (DBaaS)  
**Curso:** Ingeniería de Software I — Universidad Rafael Landívar, 2026  
**Fecha límite del hito:** 11 de septiembre de 2026  
**Equipo KoiCloud:** Hugo Escobar, Jason Gutiérrez, Jousé Menendez, Diego Joachin

## Qué contiene este paquete

| Archivo | Contenido |
|---|---|
| [`ENTREGA-2.md`](./ENTREGA-2.md) | Documento único listo para convertir a PDF / entregar |
| [`alcance.md`](./alcance.md) | Compromiso único + fuera de alcance (sin niveles) |
| [`diagramas/`](./diagramas/) | Fuentes editables Mermaid (arquitectura, UML, ER, secuencias) |
| [`mockups/`](./mockups/) | Mockups HTML de las 16 pantallas principales — piso (campos y flujos) y techo visual. Empieza por su [`README.md`](./mockups/README.md) |
| [`renders/`](./renders/) | PNG/SVG generados desde los diagramas |
| [`renders/mockups/`](./renders/mockups/) | Un PNG por pantalla + hoja completa + `mockups.pdf` |

## Piel visual y arquitectura de información

**Piso = [`mockups/`](./mockups/) (qué muestra cada pantalla); techo = [`../visual-guidelines.md`](../visual-guidelines.md) + el propio HTML (cómo se ve).**

Los mockups fijan **qué muestra cada pantalla**: campos de entrada, campos de salida, tablas y pasos del flujo. Eso es el piso y es obligatorio para W2. La **apariencia** la manda [`../visual-guidelines.md`](../visual-guidelines.md) — tema claro único sobre papel hueso, turquesa, Fraunces / Instrument Sans / IBM Plex Mono y el koi en pixel art — y [`mockups/pantallas-principales.html`](./mockups/pantallas-principales.html) ya está reconstruido en esa piel: sirve de techo visual directo, no solo de referencia de estructura. El tema oscuro preliminar de la primera versión quedó anulado. Ninguna de las dos cosas cambia el alcance sellado de [`alcance.md`](./alcance.md).

Para un agente que vaya a escribir `apps/web/**`, el bloque listo para pegar es [`../visual-guidelines-agent-prompt.md`](../visual-guidelines-agent-prompt.md).

## Compromiso en una frase

KoiCloud entrega **web + CLI + MCP** como fachadas delgadas sobre la **misma API** de control plane: usuarios, suscripciones simuladas, PostgreSQL real en Docker, consola SQL, respaldos, **doble confirmación** en mutaciones CLI/MCP, auth mínima de agente para demo, y guion de demo fiable. **No** se comprometen auto-curación como producto, seguridad completa de agentes (V2), ni validación de precio/NIT.

## Mapa diagrama → alcance

| Artefacto | Qué demuestra del compromiso |
|---|---|
| Arquitectura de componentes | Web / CLI / MCP → FastAPI + node-agent + Postgres interno |
| Despliegue | Un VPS, Compose, rutas `/api` y `/mcp`, un rango de puertos para ponds |
| Casos de uso | Cliente, Administrador + uso vía CLI/MCP (misma API) |
| Secuencia provisioning | Crear pond → job → contenedor → connection string |
| Secuencia MCP mutate+confirm | Propose → token → confirm → mutación |
| Diagrama de clases (dominio) | Usuarios, planes, ponds, jobs + `AgentAccess` mínimo |
| Modelo ER | Tablas del alcance + `agent_access` (gate de demo) |
| Mockups | Landing, auth, planes y checkout, dashboard, crear pond, detalle y conexión, consola SQL, respaldos, uso y factura, admin, acceso agente, confirmación, cuenta, estados y 404 |

## Cómo generar PDF

```bash
# Opción recomendada (si pandoc está disponible):
pandoc ENTREGA-2.md -o ENTREGA-2.pdf --pdf-engine=xelatex -V geometry:margin=2cm

# Alternativa: abrir ENTREGA-2.md / mockups en el navegador e imprimir a PDF.
```

Los renders en `renders/` ya están incrustados por referencia en `ENTREGA-2.md`.

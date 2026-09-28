---
id: W2-11
workstream: W2
persona: Jason
estado: abierto
rama: w2-acceso-agente
epica: "E9-05"
sprint: S4
pr:
---

# [W2-11] Acceso agente: revelar y rotar

## Qué se ve

Tarjeta de acceso agente en `/app/acceso-agente` con URL MCP, slug, estado habilitado/deshabilitado y contraseña visible una sola vez tras rotación, más snippets listos para copiar.

## Entradas ya decididas (no se cambian)

- Ruta: `/app/acceso-agente`.
- API: `GET /agent-access`, `POST /agent-access/rotate`, `POST /agent-access/toggle`.
- La autenticación del agente es `Basic slug:password` o `X-KOI-Agent-Password`.
- `GET /agent-access` nunca devuelve password; `rotate` la muestra una sola vez.
- Códigos de error: `agent_disabled`, `agent_bad_credentials`, `rate_limited`.
- Piel: `docs/visual-guidelines.md` §10 fila 10; la password nueva vive sobre banda `marigold`.

## Criterios de aceptación

1. La vista base muestra slug, URL, `enabled` y `rotated_at` sin revelar password.
2. Rotar muestra la nueva password una sola vez y permite copiarla.
3. Existen pestañas `Claude Code`, `Cursor` y `Genérico` con snippets en mono.
4. El toggle refleja el estado y maneja `agent_disabled` por `code`.
5. Hay prueba de render + interacción para rotar/copiar y para la ocultación posterior.

## No tocar

- `src/api/client.ts`.
- `src/api/schema.d.ts`.
- `src/lib/auth-store.ts`.
- `src/app/router.tsx` salvo una ruta que este ticket nombre y aún no exista. Las de Fase 0 ya están.
- `src/components/ui/*` salvo cambios de tema cuando el ticket lo permita.
- Cualquier archivo fuera de `apps/web/`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes endpoints, campos, hooks, rutas ni códigos de error.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

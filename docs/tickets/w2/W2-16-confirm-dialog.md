---
id: W2-16
workstream: W2
persona: Jason
estado: hecho
rama: w2-confirm-dialog
epica: E9-04
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/138"
depends_on:
---

# [W2-16] Diálogo web propose → confirm (A9 / E9-04)

## Qué se ve

En `/app/confirm`, con sesión iniciada, un velo y un diálogo con banda `marigold`. El `summary` del enlace se lee en cuerpo grande. El token va en mono. La expiración es una cuenta `mm:ss` en `warn`, con la etiqueta Expira. Confirmar es el botón primario. Descartar es el secundario. Si faltan datos, la pantalla vacía pide un enlace completo y no llama a la API. Tras confirmar, `/app` muestra «Acción confirmada.» Tras descartar, muestra «Propuesta descartada. No se ejecutó nada.»

`/app/confirmacion` abre la misma pantalla y conserva la query.

## Entradas ya decididas (no se cambian)

- Rutas nuevas bajo `RequireAuth` y `AppShell`: `confirm` y `confirmacion`.
- API existente: `POST /api/v1/confirm/{token}` y `DELETE /api/v1/confirm/{token}`. Sin body. Sin GET de pendientes.
- El tipo de propuesta sale de `ConfirmationRequiredResponse` en `schema.d.ts`. No se edita ese archivo ni OpenAPI.
- Query canónica con `token`, `summary`, `expires_at`. `location.state` solo si la query no trae ninguna de esas claves.
- Errores por `code` vía `problemToMessage`: `confirmation_not_found` (404), `confirmation_expired` (410), `confirmation_action_mismatch` (409).
- Piel de `docs/visual-guidelines.md` §6.5 y mockup pantalla 11 (`#confirmacion`). No inventar filas `action` ni «propuesto por».
- Issue #96 amendment A9 (low). Sin cambios HIGH.

## Criterios de aceptación

1. `/app/confirm` y `/app/confirmacion` exigen sesión. El alias conserva `search` y `state`.
2. Con los tres parámetros, el diálogo muestra banda marigold, summary verbatim, token en mono y cuenta `mm:ss`.
3. Confirmar hace un solo POST y navega a `/app` con el aviso «Acción confirmada.»
4. Descartar hace un solo DELETE y navega a `/app` con el aviso de propuesta descartada.
5. 404, 410 y 409 muestran el mensaje del catálogo y el `code`, y dejan Confirmar deshabilitado.
6. Sin parámetros no hay petición a `/confirm/`.
7. La prueba de página cubre el caso feliz, 404, 410 y 409.
8. A 360 px no hay scroll horizontal. El diálogo no muestra koi.

## Fuera de alcance

- Reintentar Confirmar después de 404, 410 o 409. El criterio 5 deja Confirmar apagado. No hay transición error→retry en el statechart de W2-16. Pedí un enlace nuevo.

## No tocar

- `packages/contracts/**`, `apps/web/src/api/schema.d.ts`, `apps/web/src/api/client.ts`.
- `apps/web/src/lib/errors.ts` y `apps/web/src/lib/auth-store.ts`.
- `apps/web/src/components/ui/**`.
- Cualquier ruta fuera de `apps/web/**` y `docs/tickets/w2/**`.
- OpenAPI, firmas de `app/commands/*`, y el resto de `apps/api/**`.
- `apps/web/src/features/agent-access/agent-access-page.tsx` (ya en techo de líneas; no crecer).

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará solo si hay que editar un contrato congelado o un archivo ajeno. Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`. No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

Imitá el PR #79 (`[W2-11] Acceso agente`) en el arnés de pruebas y en los hooks. El velo del diálogo sigue el patrón de `apps/web/src/features/ponds/backups-page.tsx`. Diseño sintetizado: arena candidate A + grafts (issue #96 A9).

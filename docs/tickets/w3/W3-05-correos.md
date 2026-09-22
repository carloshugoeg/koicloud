---
id: W3-05
workstream: W3
persona: Jousé
estado: abierto
rama: w3-correos
epica: "E1-01, E1-04, E8-03"
sprint: S3
pr:
---

# [W3-05] Módulo `notifications`: 4 plantillas y proveedor de consola

## Qué se ve

Módulo de notificaciones que valida contexto y renderiza correo HTML/txt con proveedor `console`. Lo visible al equipo es el log completo del correo y las plantillas en español listas para usarse.

## Entradas ya decididas (no se cambian)

- Ruta propia: `apps/api/app/modules/notifications/**`.
- API del módulo: `send(template, to, context)`.
- El proveedor `console` imprime asunto, destinatario y cuerpo completo, incluyendo URLs de verify/reset.
- Dos familias sí están fijadas por docs: verificación de correo y reset de contraseña.
- Las otras dos pertenecen a E8-03/billing, pero la lista cerrada de nombres y el copy final no están en el store.

## Criterios de aceptación

1. `send()` rechaza templates desconocidos o contexto incompleto.
2. Las cuatro plantillas renderizan versión HTML y txt una vez que W1 congele nombres/textos.
3. El proveedor `console` deja visible la URL completa en verify/reset.
4. Hay una prueba unitaria feliz por plantilla y una de validación fallida.

## No tocar

- `apps/api/app/core/**`.
- `apps/api/app/commands/**`.
- `apps/api/alembic/**`.
- `apps/api/app/modules/{ponds,jobs,nodes,backups,metering,agent_access}/**`.
- `packages/contracts/**`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes endpoints, schemas, queries, comandos ni códigos de error.
- No están congelados ni los cuatro IDs exactos ni el copy final en español; si no llegan en el ticket o desde W1, bloqueá y no inventes plantillas nuevas.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

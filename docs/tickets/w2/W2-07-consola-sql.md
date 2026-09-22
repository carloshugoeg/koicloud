---
id: W2-07
workstream: W2
persona: Jason
estado: abierto
rama: w2-consola-sql
epica: "E5-01, E5-04, E5-05"
sprint: S4
pr:
---

# [W2-07] Consola SQL (editor y tabla de resultados)

## Qué se ve

Pantalla `/app/ponds/:id/consola` con editor CodeMirror, modo lectura por defecto, resultados abajo y listado de historial. Si el árbol de esquema ya existe por contrato, se muestra; si no, no se inventa.

## Entradas ya decididas (no se cambian)

- Ruta: `/app/ponds/:id/consola`.
- API: `POST /ponds/{id}/sql` con body `{query, mode:read|write}` y `GET /ponds/{id}/sql/history`.
- Límites fijos: transacción read-only por defecto, `statement_timeout=10s` y tope de 1000 filas.
- Errores: `sql_readonly_violation` y `sql_timeout`.
- Piel: `docs/visual-guidelines.md` §10 fila 6 y §6.3; el modo write lleva borde `koi` y banda de advertencia.
- CodeMirror ya lo deja instalado W1 en Fase 0.

## Criterios de aceptación

1. Un `SELECT` muestra columnas, filas, `row_count`, `duration_ms` y `truncated`.
2. El modo por defecto es `read`; al pasar a `write` aparece el aviso visual antes de ejecutar.
3. `sql_timeout` y `sql_readonly_violation` se traducen por `code`.
4. El historial carga consultas previas y trunca visualmente las largas.
5. Si la respuesta llega truncada, se ve pie con el estado de truncamiento.
6. Hay pruebas de render + interacción para read y al menos un error del catálogo.

## No tocar

- `src/api/client.ts`.
- `src/api/schema.d.ts`.
- `src/lib/auth-store.ts`.
- `src/app/router.tsx` (si hiciera falta una ruta nueva, se pide a W1).
- `src/components/ui/*` salvo cambios de tema cuando el ticket lo permita.
- Cualquier archivo fuera de `apps/web/`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes endpoints, campos, hooks, rutas ni códigos de error.
- El mockup muestra árbol de esquema, pero `api-surface.md` no fija un endpoint para cargarlo; si hace falta pedir datos nuevos, bloqueá en vez de inventar `GET /schema`.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

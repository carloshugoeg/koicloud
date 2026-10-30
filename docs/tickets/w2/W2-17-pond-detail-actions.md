---
id: W2-17
workstream: W2
persona: Jason
estado: hecho
rama: w2-pond-detail-actions
epica: "RF-14, RF-15"
sprint: S5
pr: "https://github.com/carloshugoeg/koicloud/pull/144"
depends_on:
---

# [W2-17] Pond detail: Eliminar + Respaldar confirms (RF-14 / RF-15)

## Qué se ve

En el detalle del pond (`/app/ponds/:id`):

1. **Eliminar…** (RF-14) abre un diálogo que exige escribir el nombre exacto del pond
   antes de `DELETE /ponds/{id}`. Zona de riesgo con el mismo flujo.
2. **Respaldar ahora** (RF-15) abre un diálogo local de confirmación (banda marigold)
   antes de `POST /ponds/{id}/backups`. Mismo flujo en `/app/ponds/:id/backups`.
3. La restauración tipada por nombre en respaldos ya existe (W2-08); se conserva.
4. Detener / Iniciar / Reintentar siguen en la UI (W1-33). No se ocultan.

## Entradas ya decididas (no se cambian)

- Rutas ya registradas: `/app/ponds/:id`, `/app/ponds/:id/backups`.
- Hooks: `useTriggerBackupMutation`, `useDeletePondMutation`, `useRestoreBackupMutation`,
  `useStopPondMutation` / `useStartPondMutation` / `useRetryFailedJobMutation`.
- Confirmación web local (no token propose→confirm; eso es W2-16 / CLI / MCP).
- MSW: `DELETE /ponds/:id`, `POST /ponds/:id/backups`, restore ya cableados.
- Solo `apps/web/**` y este ticket + `00-INDEX.md`. Sin contratos congelados.
- Rama `w2-pond-detail-actions`. PR #144. Sin dependencia de #142 (cerrado out of scope).

## Criterios de aceptación

1. Detalle muestra Eliminar…; el confirm exige el nombre exacto; mismatch deja el botón
   deshabilitado; match + confirm cierra el diálogo y encola el borrado.
2. Respaldar ahora en detalle y en respaldos abre `backup-confirm-dialog` antes del POST;
   tras confirmar se ve el toast «Respaldo encolado» (sin token `X-KOI-Confirm-Token`).
3. Restore tipado por nombre sigue pasando (W2-08).
4. Detener / Iniciar siguen visibles cuando aplica (no regresión W1-33).
5. `make check-web` verde. `python3 scripts/agent_guards.py tree` verde.
6. Pruebas RF-14/15 en `detail.test.tsx` y `backups.test.tsx`.

## No tocar

- `src/api/client.ts`, `src/api/schema.d.ts`, `src/lib/auth-store.ts`.
- `src/components/ui/*` salvo tema.
- Cualquier archivo fuera de `apps/web/` y `docs/tickets/w2/`.
- Tickets ajenos (en especial W1-36). No reabrir W2-06 / W2-08.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.
No inventes endpoints, campos, hooks, rutas ni códigos de error.

## Referencia

Imitá el PR #57 (`[W2-06] Detalle del pond`) y el #56 (`[W2-08] Respaldos`): misma
estructura de archivos, MSW + Testing Library. ENTREGA-2.md RF-14 / RF-15.

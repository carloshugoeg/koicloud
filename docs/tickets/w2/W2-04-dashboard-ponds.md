---
id: W2-04
workstream: W2
persona: Jason
estado: abierto
rama: w2-dashboard-ponds
epica: "E3-02, E3-05"
sprint: S2
pr:
---

# [W2-04] Dashboard de ponds (lista y estados)

## Qué se ve

Pantalla `/app/ponds` con fila de KPI, rejilla del estanque y tabla densa de ponds. Muestra estados observados, acciones visibles y los tres data states del listado sin reordenar filas automáticamente.

## Entradas ya decididas (no se cambian)

- Ruta: `/app/ponds`.
- API: `GET /ponds`.
- Mientras haya ponds en `provisioning`, `restoring` o `deleting`, el polling es cada 4 s.
- Estados admitidos para badge: `pending`, `provisioning`, `running`, `restoring`, `stopped`, `deleting`, `deleted`, `failed`.
- La tabla replica el mockup: nombre, estado, conexión solo si corre, plan, fecha y acción.
- W1 entrega el fixture MSW con al menos 6 estados observados distintos.
- La rejilla del estanque usa celdas de 14 px según `docs/visual-guidelines.md` §6.4.

## Criterios de aceptación

1. Se ven cuatro KPI con números tabulares.
2. La rejilla muestra una celda por pond y colorea por estado.
3. La tabla oculta `host:port` cuando el pond no está corriendo.
4. Un cambio de estado hace flash de 600 ms sin mover la fila de lugar.
5. Existen los estados cargando, vacío con CTA y error con `Reintentar`.
6. Hay prueba de render y prueba con fixture MSW de cambio de estado.

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
- El nombre exacto del hook y del handler MSW de `GET /ponds` lo congela W1; si no están, bloqueá en vez de rebautizarlos.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

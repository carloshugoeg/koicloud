---
id: W2-05
workstream: W2
persona: Jason
estado: abierto
rama: w2-crear-pond
epica: "E3-01"
sprint: S3
pr:
---

# [W2-05] Crear pond (diálogo de configuración)

## Qué se ve

Diálogo sobre el dashboard para crear un pond: valida el nombre en vivo, muestra el plan heredado y, tras `202`, lleva al detalle del pond en estado de aprovisionamiento.

## Entradas ya decididas (no se cambian)

- Se monta como diálogo sobre `/app/ponds`.
- API: `POST /ponds` -> `202 {pond, job}`.
- Body fijo: `{name}`; el plan se hereda y la versión del engine es `16` de solo lectura.
- Validación de nombre: 3 a 40 caracteres, solo minúsculas, números y guiones.
- Errores: `pond_name_taken`, `quota_exceeded`, `plan_required`, `disk_full`.
- El copy y la distribución parten del mockup `#crear-pond`.

## Criterios de aceptación

1. La validación corre en vivo y el nombre final se ecoa en mono.
2. Al enviar, el botón entra en loading y el `202` lleva al detalle con badge de provisioning.
3. Los errores `pond_name_taken` y `quota_exceeded` salen del catálogo existente.
4. Si llega `plan_required`, la salida visible lleva a planes en vez de dejar al usuario atrapado.
5. Hay prueba de interacción para el flujo feliz y al menos un error del catálogo.

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
- Si el detalle `/app/ponds/:id` o el hook de create no quedaron congelados por W1, bloqueá; no abras rutas nuevas desde este ticket.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

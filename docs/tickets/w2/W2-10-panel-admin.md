---
id: W2-10
workstream: W2
persona: Jason
estado: abierto
rama: w2-panel-admin
epica: "E8-01, E8-02, E8-03, E8-04"
sprint: S4
pr:
---

# [W2-10] Panel administrador (tres tablas)

## Qué se ve

Área admin sin koi, con tres tablas densas: usuarios, ponds del sistema y bitácora. El guard de rol evita ver la superficie si el JWT no trae `role=admin`.

## Entradas ya decididas (no se cambian)

- La pantalla corresponde al mockup `#admin`; la división en una ruta o subrutas la congela W1.
- Role guard: `admin_only` cuando el usuario no es admin.
- API: `GET /admin/users`, `POST /admin/users/{id}/suspend`, `POST /admin/users/{id}/reactivate`, `GET /admin/ponds`, `GET /admin/audit`.
- La suspensión exige escribir el dato de confirmación del mockup y un motivo visible.
- Suspender no detiene ponds ni borra datos del usuario.
- La paginación es por cursor y la bitácora se ve en mono.

## Criterios de aceptación

1. La tabla de usuarios muestra plan activo y cantidad de ponds.
2. Los diálogos de suspender/reactivar piden la confirmación esperada y no actúan en un solo clic.
3. La tabla de ponds soporta filtros de usuario/estado ya sellados por la API.
4. La bitácora lista solo eventos sensibles devueltos por el backend.
5. Un usuario no admin ve el estado prohibido mapeado desde `admin_only`.
6. Hay pruebas de render + interacción para una tabla y una mutación admin.

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
- Si W1 no congeló si este panel vive en una sola ruta o en `/app/admin/*`, bloqueá y pedí aclaración; no rediseñes la navegación desde W2.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

---
id: W2-08
workstream: W2
persona: Jason
estado: abierto
rama: w2-respaldos
epica: "E6-02, E6-03"
sprint: S3
pr:
---

# [W2-08] Respaldos: lista y restauración

## Qué se ve

Pantalla `/app/ponds/:id/respaldos` con tabla de backups y diálogo de restauración que exige escribir el nombre exacto del pond antes de confirmar.

## Entradas ya decididas (no se cambian)

- Ruta: `/app/ponds/:id/respaldos`.
- API: `GET /ponds/{id}/backups` y `POST /ponds/{id}/restore` con `{backup_id}`.
- En web la confirmación es textual con el nombre del pond; aquí no aplica `propose -> confirm token`.
- Tipos de backup: `daily`, `on_demand`, `pre_delete`.
- La tabla muestra tipo, estado, tamaño, `sha256`, fecha y expiración.
- W1 entrega un fixture con al menos tres backups para MSW.
- El mockup nombra `backup_not_found`, `backup_not_restorable` y `confirm_name_mismatch`, pero esos códigos no aparecen en `api-surface.md` §7.

## Criterios de aceptación

1. La tabla lista los backups con su chip `pre_delete` cuando corresponda.
2. El diálogo de restore no habilita confirmar hasta que el nombre escrito coincida exacto.
3. La vista tiene estados cargando, vacío y error.
4. Un restore feliz envía el `backup_id` escogido y muestra el estado encolado.
5. Hay prueba de interacción para la confirmación por nombre.

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
- Usá solo códigos del catálogo de `api-surface.md` §7. No inventes uno desde web.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

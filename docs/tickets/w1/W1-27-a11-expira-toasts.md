---
id: W1-27
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-a11-expira-toasts
epica: "#96 A11"
sprint:
pr: "https://github.com/carloshugoeg/koicloud/pull/134"
depends_on:
---

# [W1-27] Columna Expira y toasts de 1.2 s

Issue [#96](https://github.com/carloshugoeg/koicloud/issues/96), enmienda A11.

## Qué se ve

La tabla de respaldos llena **Expira** con `en N d`, `hoy`, `vencido` o `—`, según `expires_at`. El título de la celda es el instante en `America/Guatemala`. Un toast de 1.2 s confirma «URI copiada», «Respaldo encolado» y «Reintento encolado». **Respaldar ahora** está en el encabezado de respaldos y en el detalle cuando el pond está en línea. **Reintentar** está en el detalle cuando `observed_state` es `failed`.

## Entradas ya decididas (no se cambian)

- `BackupOut.expires_at` es derivado. No hay columna nueva ni migración.
- `expires_at_for(backup)` vive en `apps/api/app/modules/backups/retention.py`. `BACKUP_RETENTION_DAYS = 7` no es argumento.
- Devuelve `None` si `status` no es `succeeded` o si `kind` es `pre_delete`. En otro caso, `created_at` más 7 días, en UTC.
- La web no calcula la retención. `formatExpires` solo recibe el ISO. `null` se muestra como `—`.
- Toast propio: `toast({ tone, message })` y un `<ToastHost />`. La duración de 1200 ms vive en el host. Sin paquete `sonner`.
- Piel: fondo `bone-raised`, borde izquierdo de 3 px semántico, `--shadow-print`, radio 2. Sin iconos saturados.
- Con `prefers-reduced-motion` no hay movimiento. El toast igual sale a los 1.2 s.
- Copiar la URI mantiene la etiqueta del botón 1.2 s y además el toast «URI copiada».
- Restaurar sigue con la banda `restore-queued` y el id del job. No hay toast de éxito de restore.
- El error de esas mutaciones usa `problemToMessage`.
- `POST /ponds/{id}/backups` y `POST /ponds/{id}/retry` ya existen. La web los llama y espera 202, sin `propose → confirm`.
- Hay que partir `backups-page.tsx` antes de añadir la celda y el botón. La página queda en 250 líneas o menos.
- No hay stop/start ni motivo de suspensión.

## Criterios de aceptación

1. `GET /ponds/{id}/backups` trae `expires_at` nulo si el respaldo no está `succeeded`, y `created_at` más 7 días si está `succeeded` y no es `pre_delete`.
2. La columna **Expira** no queda siempre en `—` cuando el fixture trae `expires_at`.
3. El toast visible desaparece a los 1200 ms.
4. Copiar la URI deja la etiqueta «URI copiada» y muestra el toast.
5. **Respaldar ahora** y **Reintentar** hacen POST con estado 202, no 409, y muestran «Respaldo encolado» o «Reintento encolado».
6. `make contracts` regenera OpenAPI y `schema.d.ts`. `make check-api` y `make check-web` pasan.

## No tocar

- Migraciones Alembic y la tabla `backups`.
- Firmas de `app/commands/*`.
- Stop/start (A5) y el motivo de suspensión (#121).
- El paquete `sonner`.
- `packages/contracts/openapi.json` y `apps/web/src/api/schema.d.ts` editados a mano.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.
No inventes endpoints, columnas ni un flujo de confirmación para la web.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

---
id: W2-09
workstream: W2
persona: Jason
estado: en_curso
rama: w2-uso-y-facturas
epica: "E7-03, E2-03, E2-06"
sprint: S3
pr: "https://github.com/carloshugoeg/koicloud/pull/51"
---

# [W2-09] Uso del mes e historial de facturas

## Qué se ve

Pantalla `/app/uso?month=YYYY-MM` con KPI del mes, gráfico de tendencia, desglose por pond y factura visible sobre `paper`, lista para descargar en PDF.

## Entradas ya decididas (no se cambian)

- Ruta: `/app/uso?month=YYYY-MM`.
- API: `GET /usage`, `GET /invoices`, `GET /invoices/{id}` y `GET /invoices/{id}/pdf`.
- El response de uso trae `month`, `total_instance_hours`, `total_storage_gb_hours` y `ponds[]`.
- La factura muestra líneas, subtotal, IVA 12 % y total.
- Piel: `docs/visual-guidelines.md` §10 fila 8 y §6.4 para los gráficos.
- La descarga PDF usa el endpoint binario ya sellado, no una renderización del frontend.

## Criterios de aceptación

1. Cambiar el mes actualiza la request y el estado visible.
2. Se ven KPI, tendencia y desglose por pond sin mezclar copy libre con números del API.
3. El detalle de factura se renderiza sobre `paper` con subtotal, IVA y total.
4. La acción de descargar PDF consume el blob del backend.
5. Existe estado vacío para meses sin datos.
6. Hay prueba de render/interacción para cambio de mes y descarga PDF.

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

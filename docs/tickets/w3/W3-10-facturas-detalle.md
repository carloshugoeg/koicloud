---
id: W3-10
workstream: W3
persona: Jousé
estado: en_revision
rama: w3-facturas-detalle
epica: "E2-03"
sprint: S4
pr: https://github.com/carloshugoeg/koicloud/pull/69
---

# [W3-10] `GET /invoices/{id}` y `/pdf`

## Qué se ve

Detalle de invoice y descarga PDF del mismo documento. Lo visible es el JSON de detalle y el adjunto `application/pdf` con ownership correcto.

## Entradas ya decididas (no se cambian)

- Endpoints: `GET /invoices/{id}` y `GET /invoices/{id}/pdf`.
- Detalle responde `{invoice, lines[]}`.
- La descarga responde `application/pdf` y `Content-Disposition: attachment`.
- Si el archivo falta en disco, se regenera desde la factura almacenada.
- Errores: `not_owner` o 404 según el contrato congelado.
- La factura es la fila persistida (G1, #54). El cableado del comando llegó en #50. Este ticket cubre el HTTP: detalle, headers y regeneración si falta el archivo.

## Criterios de aceptación

1. El detalle incluye invoice, líneas, subtotal, IVA y total.
2. La descarga PDF sale con headers correctos.
3. Pedir una factura ajena devuelve la protección de ownership del contrato.
4. Hay pruebas de API para detalle, download y regeneración al faltar el archivo.

## No tocar

- `apps/api/app/core/**`.
- `apps/api/app/commands/**`.
- `apps/api/alembic/**`.
- `apps/api/app/modules/{ponds,jobs,nodes,backups,metering,agent_access}/**`.
- `packages/contracts/**`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes endpoints, schemas, queries, comandos ni códigos de error.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

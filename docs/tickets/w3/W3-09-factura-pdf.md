---
id: W3-09
workstream: W3
persona: Jousé
estado: abierto
rama: w3-factura-pdf
epica: "E2-03"
sprint: S3
pr:
---

# [W3-09] Factura PDF con `fpdf2` e IVA desglosado

## Qué se ve

Generador de PDF de factura a partir de un `invoice` ya calculado. El resultado visible es un archivo PDF legible con código `KC-...`, desglose de IVA y pie académico.

## Entradas ya decididas (no se cambian)

- Módulo: `apps/api/app/modules/billing/invoice_pdf.py`.
- Formato de código: `KC-{año}-{seq:06d}`.
- Fuente base: Helvetica.
- Pie fijo: `Factura simulada — proyecto académico`.
- Ejemplo Micro: subtotal `4.4643`, IVA `0.5357`, total `5.0000`.
- El PDF se guarda bajo `INVOICE_DIR`.
- El store no trae el golden PDF ni el JSON de `invoice` prometidos por la planificación.

## Criterios de aceptación

1. El PDF generado pesa más de 1 KB y se guarda bajo `INVOICE_DIR`.
2. El documento incluye línea de IVA 12 % y el pie académico.
3. Hay prueba unitaria para el alineado de `split_iva` y los totales.
4. La función renderiza desde un objeto de factura ya calculado, sin rehacer billing.

## No tocar

- `apps/api/app/core/**`.
- `apps/api/app/commands/**`.
- `apps/api/alembic/**`.
- `apps/api/app/modules/{ponds,jobs,nodes,backups,metering,agent_access}/**`.
- `packages/contracts/**`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes endpoints, schemas, queries, comandos ni códigos de error.
- Si W1 no entrega el golden PDF y el JSON de ejemplo, bloqueá y no fabriques un fixture “parecido”.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

---
id: W1-31
workstream: W1
persona: Carlos
estado: hecho
rama: w1-nit-checkout-invoice
epica: "E2-02, E2-06"
sprint: S4
pr: https://github.com/carloshugoeg/koicloud/pull/133
depends_on:
---

# [W1-31] NIT en checkout → factura (#96 A2)

## Qué se ve

En `/app/planes` el diálogo de checkout envía el NIT (o `CF`) al contratar. La factura
resultante —respuesta de `POST /subscriptions`, detalle en `/app/uso` y PDF— muestra el
NIT del receptor, las líneas de pago y el total del backend. Desaparece
`INVOICE_BREAKDOWN` hardcodeado en el cliente.

## Entradas ya decididas (no se cambian)

- **CCR aprobado:** [#127](https://github.com/carloshugoeg/koicloud/issues/127) (amendment r3,
  issue [#96](https://github.com/carloshugoeg/koicloud/issues/96) comment).
- `users.nit` ya existe; sin migración.
- `SubscribeRequest.nit` opcional; `InvoiceOut.nit`; PDF con NIT; web envía y muestra montos
  del API.
- **No tocar** PR [#123](https://github.com/carloshugoeg/koicloud/pull/123) (`PlanOut` /
  `formatPrice`).
- **No tocar** PR [#121](https://github.com/carloshugoeg/koicloud/pull/121) (suspend reason).
- Autor de commits: Carlos Hugo Escobar. Sin merge / LGTM hasta «Carlos yes».

## Criterios de aceptación

1. `POST /subscriptions` acepta `nit` opcional y, si viene, actualiza `users.nit`.
2. `InvoiceOut.nit` y el PDF muestran el NIT del receptor (o `CF` / null según contrato).
3. Checkout envía el NIT del formulario; ya no usa `INVOICE_BREAKDOWN` para montos.
4. `/app/uso` `InvoicePaper` muestra NIT + líneas + subtotal/IVA/total del API.
5. Pruebas API + UI (MSW) del caso feliz con NIT y sin NIT.
6. Capturas / proof embebidos en el cuerpo del PR. PR queda **abierto** (no merge).

## No tocar

- Rama / PR #123 (`w1-plans-pricing`) salvo rebase posterior acordado.
- PR #121 / CCR #125 (motivo de suspensión).
- Migraciones Alembic (no hacen falta).
- Firmas de comandos ajenos a `subscribe` / mappers de invoice.
- `PlanOut` pricing fields (#123).

## Si algo falta

Nada: CCR #127 aprobado. Implementación en este PR.

## Referencia

CCR [#127](https://github.com/carloshugoeg/koicloud/issues/127); amendment r3;
issue [#96](https://github.com/carloshugoeg/koicloud/issues/96)#issuecomment-6445716121.

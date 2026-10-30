# Snapshot de NIT en InvoiceOut

## Status

Accepted. CCR [#127](https://github.com/carloshugoeg/koicloud/issues/127).

## Context

El checkout pide un NIT (o `CF`) al contratar. La factura en `/app/uso`, el PDF y
cualquier cliente sin `GET /me` deben mostrar el NIT del receptor. No hay migración:
`users.nit` ya existe.

## Decision

`SubscribeRequest.nit` opcional (trim, vacío→null, `CF` ok, max 32) actualiza
`users.nit` al suscribir. `InvoiceOut.nit` se rellena desde `users.nit` en el
momento de emitir/serializar la factura (y el PDF lo imprime). La web envía `nit`
y deja de inventar montos con `INVOICE_BREAKDOWN`.

## Consequences

Sin columna en `invoices`, un `PATCH /me` posterior puede cambiar el NIT que ven
facturas ya emitidas al volver a serializarlas. Se rechazó leer solo `/me` en la
UI (el PDF y otros clientes no lo verían) y una migración de snapshot (fuera de
alcance de este CCR).

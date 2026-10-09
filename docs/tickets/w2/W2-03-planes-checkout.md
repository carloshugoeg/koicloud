---
id: W2-03
workstream: W2
persona: Jason
estado: hecho
rama: w2-planes-checkout
epica: "E2-01, E2-02"
sprint: S2
pr: "https://github.com/carloshugoeg/koicloud/pull/48"
---

# [W2-03] Catálogo de planes y contratación

## Qué se ve

Ruta `/app/planes` con tabla comparativa densa, tarjetas de los tres planes y diálogo de checkout. Tras contratar, la UI muestra la suscripción activa y lleva al usuario al siguiente paso de creación de pond.

## Entradas ya decididas (no se cambian)

- Ruta: `/app/planes`.
- API: `GET /plans` y `POST /subscriptions`.
- Planes fijos: Sandbox USD 0 / 10 min / 1 pond / 1 GB; Micro USD 5 / mes / 1 pond / 1 GB / backups 7 d; Pro USD 0.02·h / 10 ponds / 20 GB.
- Respuesta de contratación: `{subscription, invoice, payment}`.
- La factura Micro de ejemplo debe mostrar subtotal `4.4643`, IVA `0.5357` y total `5.0000`.
- El diálogo lleva aviso fijo `Pago simulado: no se realiza ningún cobro real.` y helper `CF si no tienes NIT`.
- Error fijo: `plan_required`. No existe `payment_failed` ni código de tarjeta
  rechazada. El pago simulado siempre pasa; no inventes un `code` nuevo.
- Piel: `docs/visual-guidelines.md` §10 fila 2.

## Criterios de aceptación

1. Los tres planes salen de la API y se ven tanto en tabla como en tarjeta sin reescribir valores a mano.
2. El checkout muestra el aviso fijo y valida los campos esperados antes de enviar.
3. La contratación exitosa muestra toast/estado final y CTA o redirección hacia creación de pond.
4. La vista de factura previa usa los valores de subtotal/IVA/total del fixture sellado.
5. Los errores se resuelven por `code`, no por comparar el `message`.
6. Hay pruebas de render + submit con MSW para caso feliz y error.

## No tocar

- `src/api/client.ts`.
- `src/api/schema.d.ts`.
- `src/lib/auth-store.ts`.
- `src/app/router.tsx` salvo una ruta que este ticket nombre y aún no exista. Las de Fase 0 ya están.
- `src/components/ui/*` salvo cambios de tema cuando el ticket lo permita.
- Cualquier archivo fuera de `apps/web/`.

## Si algo falta

Respondé `BLOQUEADO` solo si hay que agregar un `code` al catálogo.
No hay rechazo de tarjeta en v0. Usá `plan_required` y el caso feliz.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

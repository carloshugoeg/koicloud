---
id: W1-54
workstream: W1
persona: Carlos
estado: hecho
rama: w1-plan-onboarding
epica: "E2-02"
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/242"
depends_on:
---

# [W1-54] Plan onboarding: sandbox default + first-login chooser + confirm password

## Qué se ve

1. Un registro nuevo crea una suscripción `sandbox` activa (no Micro).
2. El primer login autenticado muestra una pantalla de planes: Micro, Pro y
   "Continuar gratis (modo sandbox)". Tras elegir, no vuelve a aparecer.
3. Micro/Pro abren el checkout simulado existente. Continuar gratis entra a la app
   con sandbox.
4. El formulario de registro pide "Confirmar contraseña"; si no coincide, error
   claro y no se envía.

## Entradas ya decididas (no se cambian)

- Firma de `register_user(payload) -> RegisterUserResponse` sin `plan_id`.
- Checkout: `POST /api/v1/subscriptions` + `CheckoutModal` / `useSubscribeMutation`.
- Confirm password solo en cliente (patrón de `reset-page.tsx`); sin campo nuevo en
  `RegisterUserRequest` salvo que el contrato lo haga trivial.
- Persistencia del "ya eligió" en servidor (columna en `users` + campo en `UserOut`).
- Statechart: `docs/statechart/level2/plan-onboarding.md`.
- No tocar `commands/auth.py` `send_reset_token` ni plantillas de notifications (#239).

## Criterios de aceptación

1. Tras `POST /auth/register` (usuario nuevo), existe exactamente una suscripción
   `active` con `plan_id=sandbox`.
2. Re-registro no verificado no inserta una segunda suscripción.
3. Con `UserOut.onboarded=false` (`users.onboarded_at` null), un usuario autenticado
   es redirigido a `/app/onboarding` (también tras reload / `PublicOnly`).
4. "Continuar gratis" llama `POST /me/onboarding/complete` (204) y deja `plan_id=sandbox`;
   no llama subscribe.
5. Micro/Pro reutilizan el checkout existente (con card) y luego marcan el flag.
6. Tras una elección, el onboarding no se muestra otra vez.
7. `ensure_subscription` no inserta Micro silencioso encima de un sandbox activo
   (incluido periodo vencido mientras status=active).
8. Confirm password mismatch bloquea el submit en cliente con mensaje claro.
9. `make check-api` y checks web pasan.

## No tocar

- `apps/api/app/commands/auth.py` rutas de reset (`send_reset_token`) / templates de
  notifications (PR #239).
- `.github/scripts/check_ownership.py` y CI.
- Secretos, env de prod, datos reales.
- Rebase / force-push (solo merge commits).

## Si algo falta

`BLOQUEADO` solo si hace falta un CCR de contrato (columna `users` + `UserOut`) sin
aprobación de W1. Migración mínima + `make contracts` permitidos con justificación.

## Referencia

Statechart Fixed vs AsIs en `docs/statechart/model/plan-onboarding/`.
Patrón confirm password: `apps/web/src/features/auth/reset-page.tsx`.
Checkout: `apps/web/src/features/plans/checkout-modal.tsx`.

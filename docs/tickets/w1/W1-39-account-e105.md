---
id: W1-39
workstream: W1
persona: Carlos
estado: en_revision
rama: w1-account-e105
epica: "E1-05"
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/148"
depends_on:
---

# [W1-39] Account E1-05 — DELETE /me, change-password, resend-verification (CCR #126)

Implementa el CCR aprobado [#126](https://github.com/carloshugoeg/koicloud/issues/126)
(amendment r3). Supersede r2 A6 paths `/me/password` y `/auth/verify/resend`.

## Qué se ve

- `DELETE /me {confirm_email}` → 202 soft-delete (`users.deleted_at`, email tombstone).
- `POST /me/change-password` → 204; revoca otros refresh tokens.
- `POST /auth/resend-verification` → siempre 202; rate 3/min/IP.
- Password min 8→10 en register / reset / change (OpenAPI, Pydantic, commands).
- Error nuevo `email_mismatch` 422.
- Web `/app/account`: perfil, cambio de contraseña, eliminar cuenta, reenvío si no verificado.

## Entradas ya decididas (no se cambian)

- CCR #126 aprobado en issue #96 comment (r3).
- Migración W1: `users.deleted_at`.
- Firmas: `resend_verification`, `change_password`, `delete_me` (+ helper `delete_all_user_ponds`).
- No tocar PlanOut / #123.

## Criterios de aceptación

1. 9-char password → 422 `password_too_weak` en register, reset y change-password.
2. email mismatch en DELETE /me → 422 `email_mismatch`.
3. resend unknown email → 202; rate limit 3/min/IP → 429 `rate_limited`.
4. delete soft-delete: login falla; sub cancelada; ponds encolados; audit `user.delete`.
5. Migración up/down de `users.deleted_at`.
6. Preview `/app/account` password change, delete, resend.

## No tocar

- PlanOut / pricing (#123).
- Ticket W1-34 / INDEX hecho de #147 (ajeno a esta rama).

## Si algo falta

`BLOQUEADO` solo si hay que editar otro contrato fuera de #126.

## Referencia

- https://github.com/carloshugoeg/koicloud/issues/126
- https://github.com/carloshugoeg/koicloud/issues/96#issuecomment-6445716121

---
id: W1-15
workstream: W1
persona: Carlos
estado: hecho
rama: w1-auth-persist
epica: "E1-01, E1-02, E1-03, E1-04"
sprint: S1
pr: https://github.com/carloshugoeg/koicloud/pull/7
depends_on:
---

# [W1-15] Persistencia de `users` y `email_tokens`

## Qué se ve

`register_user`, `verify_email`, `send_reset_token`, `reset_password`, `issue_tokens`, `rotate_refresh` y `revoke_refresh` dejan de devolver fixtures. W3 solo llama `app/commands/auth.py`. El plaintext de un token de correo sale una vez, por `issue_email_token`.

## Entradas ya decididas (no se cambian)

- Firmas congeladas en `commands/auth.py`. OpenAPI no cambia.
- `POST /auth/verify` recibe `{token}` en body. PR #2.
- Token de email: estado `issued → consumed | expired`. Kind `verify_email | reset_password`. SHA-256 only.
- Mismo correo → `email_taken`. Re-verify de token consumido → `token_invalid`. Forgot de correo desconocido → `{ok:true}`.
- ORM en `core/models.py` (`EmailToken`, `RefreshToken`). Tabla ya existe en `0001_initial`.

## Criterios de aceptación

1. Register inserta `users` (argon2id, `email_verified_at` null) y un `email_tokens` de 24 h.
2. Verify consume el token, escribe `email_verified_at` y un segundo verify falla con `token_invalid`.
3. `issue_email_token(user_id, kind)` devuelve el plaintext una vez para que W3 mande correo.
4. Forgot siempre `{ok:true}` e inserta reset de 1 h solo si el usuario existe.
5. Reset cambia el hash y revoca `refresh_tokens`. Login y rotación persisten refresh.

## No tocar

- `packages/contracts/**`.
- `apps/api/app/modules/auth/**`.
- Endpoints y schemas.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.

## Referencia

El persist de ponds en PR #6. Tests contra Postgres real, sin mock del comando bajo prueba.

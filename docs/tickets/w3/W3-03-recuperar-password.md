---
id: W3-03
workstream: W3
persona: Jousé
estado: abierto
rama: w3-recuperar-password
epica: "E1-04"
sprint: S3
pr:
depends_on: W1-15 W3-01
---

# [W3-03] `POST /auth/forgot` y `/auth/reset`

## Qué se ve

Endpoints para recuperación de contraseña con respuesta neutral en forgot y consumo de token temporal en reset. Lo visible es el contrato HTTP y la revocación de sesiones posterior al cambio.

## Entradas ya decididas (no se cambian)

- Endpoints: `POST /auth/forgot` -> `send_reset_token` y `POST /auth/reset` -> `reset_password`.
- Forgot siempre devuelve `202 {ok:true}`.
- Reset devuelve `{ok:true}` y revoca todos los refresh del usuario.
- TTL fijo del token de reset: 1 h y un solo uso.
- Errores: `token_invalid`, `token_expired`, `password_too_weak`, `rate_limited`.
- Depends on W1-15 landed. Call `send_reset_token`, `reset_password` and
  `issue_email_token` only.
- W1 ya persiste el reset: `send_reset_token` inserta `email_tokens` (`kind=reset_password`, 1 h) si el usuario existe. El plaintext sale por `issue_email_token(user_id, reset_password)`. `reset_password` consume el token y revoca `refresh_tokens`.

## Criterios de aceptación

1. El router llama `send_reset_token`. Forgot devuelve 202 aun cuando el correo no exista.
2. El router llama `reset_password`. El comando actualiza el hash y revoca sesiones.
3. Token inválido o expirado devuelve el `code` correcto (el comando).
4. El mismo token no puede reutilizarse (el comando).
5. Hay pruebas de API para forgot neutral y reset feliz.

## No tocar

- `apps/api/app/core/**`.
- `apps/api/app/commands/**`.
- `apps/api/alembic/**`.
- `apps/api/app/modules/{ponds,jobs,nodes,backups,metering,agent_access}/**`.
- `packages/contracts/**`.

## Si algo falta

Respondé `BLOQUEADO` solo si hay que *editar* OpenAPI o la firma de un comando.
El persist de `email_tokens` ya está en W1-15. Llamá los comandos.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

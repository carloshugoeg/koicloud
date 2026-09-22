---
id: W3-03
workstream: W3
persona: Jousé
estado: abierto
rama: w3-recuperar-password
epica: "E1-04"
sprint: S3
pr:
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

## Criterios de aceptación

1. Forgot devuelve 202 aun cuando el correo no exista.
2. Reset con token válido actualiza el password hash y revoca sesiones.
3. Token inválido o expirado devuelve el `code` correcto.
4. El mismo token no puede reutilizarse.
5. Hay pruebas de API para forgot neutral y reset feliz.

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

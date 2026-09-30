---
id: W3-01
workstream: W3
persona: Jousé
estado: hecho
rama: w3-registro-verificacion-v2
epica: "E1-01, E1-02"
sprint: S2
pr: "#10"
depends_on: W1-15
---

# [W3-01] `POST /auth/register` y `POST /auth/verify`

## Qué se ve

Dos endpoints de auth ya cerrados por contrato para que Web pueda registrar y verificar correo sin tocar invariantes de token. El resultado observable es el response JSON correcto y las pruebas de API en verde.

## Entradas ya decididas (no se cambian)

- Endpoints: `POST /auth/register` -> `register_user` y `POST /auth/verify` -> `verify_email`.
- Register responde `{user_id, email_verified:false}`.
- Verify responde `{user_id, email_verified:true}`.
- Verify recibe el token **solo** en body JSON `VerifyEmailRequest` `{token}` (OpenAPI / `api-surface.md`). No existe `POST /auth/verify?token=`. El enlace de correo puede aterrizar en Web con `?token=`; el router de W3 lee el body.
- Errores: `email_taken`, `password_too_weak`, `token_invalid`, `token_expired`, `rate_limited`.
- Depends on W1-15 landed (`be147a5`). Call `register_user`, `verify_email` and
  `issue_email_token` only. Do not edit `core/` or `commands/`.
- Las firmas de `register_user` y `verify_email` las deja W1; el router solo valida y transporta.
- W1 ya persiste `users` y `email_tokens`. El router llama esos comandos y `issue_email_token(user_id, verify_email)` para obtener el plaintext del correo. No hay `token` en `RegisterUserResponse`.

## Criterios de aceptación

1. El router de `modules/auth` llama `register_user` y `issue_email_token`. El persist del usuario lo hace el comando.
2. El router llama `verify_email`. El comando marca `email_verified_at` y consume el token.
3. Correo duplicado devuelve `email_taken` 409 (el comando; el router transporta el `AppError`).
4. Token inválido o expirado devuelve el `code` del catálogo y ejemplo de schema coherente.
5. Hay pruebas de API para caso feliz y token expirado. No reimplementes el persist en el test.

## No tocar

- `apps/api/app/core/**`.
- `apps/api/app/commands/**`.
- `apps/api/alembic/**`.
- `apps/api/app/modules/{ponds,jobs,nodes,backups,metering,agent_access}/**`.
- `packages/contracts/**`.

## Si algo falta

Respondé `BLOQUEADO` solo si hay que *editar* OpenAPI, una firma de comando o `core/`.
`users` / `EmailToken` en `core/models.py` no es un muro: W1-15 ya los dejó. Llamá los comandos.
Si `depends_on` no está hecho, `ESPERA`. No inventes endpoints, schemas, queries ni códigos.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

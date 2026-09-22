---
id: W3-01
workstream: W3
persona: Jousé
estado: abierto
rama: w3-registro-verificacion
epica: "E1-01, E1-02"
sprint: S2
pr:
---

# [W3-01] `POST /auth/register` y `POST /auth/verify`

## Qué se ve

Dos endpoints de auth ya cerrados por contrato para que Web pueda registrar y verificar correo sin tocar invariantes de token. El resultado observable es el response JSON correcto y las pruebas de API en verde.

## Entradas ya decididas (no se cambian)

- Endpoints: `POST /auth/register` -> `register_user` y `POST /auth/verify` -> `verify_email`.
- Register responde `{user_id, email_verified:false}`.
- Verify responde `{user_id, email_verified:true}`.
- Errores: `email_taken`, `password_too_weak`, `token_invalid`, `token_expired`, `rate_limited`.
- Las firmas de `register_user` y `verify_email` las deja W1; el router solo valida y transporta.
- La documentación choca en el transporte del token de verify (`?token=` vs body JSON).

## Criterios de aceptación

1. Register persiste al usuario y dispara la notificación de verificación.
2. Verify marca `email_verified_at` y consume el token una sola vez.
3. Correo duplicado devuelve `email_taken` 409.
4. Token inválido o expirado devuelve el `code` del catálogo y ejemplo de schema coherente.
5. Hay pruebas de API para caso feliz y token expirado.

## No tocar

- `apps/api/app/core/**`.
- `apps/api/app/commands/**`.
- `apps/api/alembic/**`.
- `apps/api/app/modules/{ponds,jobs,nodes,backups,metering,agent_access}/**`.
- `packages/contracts/**`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes endpoints, schemas, queries, comandos ni códigos de error.
- Antes de codear, W1 debe congelar si verify recibe el token por query (`POST /auth/verify?token=`) o por body; no abras dos variantes.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

---
id: W3-02
workstream: W3
persona: Jousé
estado: abierto
rama: w3-login-sesion
epica: "E1-03"
sprint: S2
pr:
---

# [W3-02] `POST /auth/login`, `/refresh`, `/logout`

## Qué se ve

Cableado de sesión JWT + refresh para que Web y CLI puedan iniciar sesión, rotar refresh y cerrar sesión con el contrato sellado.

## Entradas ya decididas (no se cambian)

- Endpoints: `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`.
- Comandos: `issue_tokens`, `rotate_refresh`, `revoke_refresh`.
- Login responde `{access_token, refresh_token, user}`; logout responde `204`.
- Refresh token va en cookie `koi_refresh`; JWT 15 min y refresh 30 días, rotativo.
- Errores: `invalid_credentials`, `email_not_verified`, `account_suspended`, `token_expired`, `rate_limited`.

## Criterios de aceptación

1. Login exitoso devuelve JWT, refresh y usuario actual.
2. Refresh rota el token y revoca el anterior.
3. El reuso de un refresh revoca la familia y falla por la vía sellada.
4. Logout devuelve `204` y limpia la sesión actual.
5. Hay pruebas de API para login, refresh, logout y cuenta suspendida.

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

---
id: W3-02
workstream: W3
persona: Jousé
estado: en-revision
rama: w3-login-sesion
epica: "E1-03"
sprint: S2
pr:
depends_on: W1-15 W3-01
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
- Depends on W1-15 landed and W3-01 (register/verify against the real command).
  Call `issue_tokens`, `rotate_refresh` and `revoke_refresh` only.
- W1 ya persiste login y refresh. `issue_tokens` exige usuario verificado. `rotate_refresh` rota y, si se reusa un refresh revocado, revoca la familia. `revoke_refresh(token)` revoca uno. El logout actual en `api_v1.py` llama `revoke_all_refresh_tokens(user_id)` (204). El router de W3 debe, además, leer la cookie `koi_refresh` y preferir `revoke_refresh(token)` cuando el refresh esté presente.

## Criterios de aceptación

1. El router llama `issue_tokens`. Login exitoso devuelve JWT, refresh y usuario actual.
2. El router llama `rotate_refresh`. Refresh rota el token y revoca el anterior.
3. El reuso de un refresh revoca la familia y falla por la vía sellada (el comando).
4. Logout llama `revoke_refresh` con el refresh de la cookie y responde `204`.
5. Hay pruebas de API para login, refresh, logout y cuenta suspendida.

## No tocar

- `apps/api/app/core/**`.
- `apps/api/app/commands/**`.
- `apps/api/alembic/**`.
- `apps/api/app/modules/{ponds,jobs,nodes,backups,metering,agent_access}/**`.
- `packages/contracts/**`.

## Si algo falta

Respondé `BLOQUEADO` solo si hay que *editar* OpenAPI o la firma de un comando.
Los refresh en `core/` no son un muro. Llamá los comandos. Si W3-01 no está hecho, `ESPERA`.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

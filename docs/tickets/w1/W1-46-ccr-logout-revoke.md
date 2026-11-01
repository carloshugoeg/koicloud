---
id: W1-46
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-ccr-logout-revoke
epica: E1-03
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/167"
depends_on: W1-45
---

# [W1-46] Revocar el access token al cerrar sesión

## Qué se ve

**Cerrar sesión** llama `POST /auth/logout` con el bearer de la sesión. El servidor revoca ese refresh y el `jti` del access token. Una llamada posterior con ese mismo bearer responde 401 `token_invalid`, y la Web vuelve al login.

Si ese POST falla por red o responde 5xx, la pantalla igual vuelve al login. `localStorage` queda con `koi_logged_out` en `pending`. Aparece el aviso "La sesión puede seguir activa en el servidor." La acción no deja una promesa rechazada.

## Entradas ya decididas (no se cambian)

- Un solo cierre de sesión visible. `logoutSession` en `apps/web/src/api/hooks/auth.ts`. El reintento de arranque llama `retryLogoutQuietly`, que usa el mismo POST.
- Marcador `koi_logged_out` (`pending` / `settled`) de W1-45. El aviso es el texto de arriba.
- `POST /auth/logout` sigue respondiendo 204. El 401 usa el código `token_invalid` que ya está en el catálogo.
- CCR #96 r6-7(a). Depends on W1-45, hecho.

## Criterios de aceptación

1. Tras logout, `GET /api/v1/me` con el mismo bearer responde 401. Prueba `test_logout_rejects_reused_access_token`.
2. **Cerrar sesión** envía `Authorization: Bearer` y deja el encabezado «Iniciar sesión». Prueba `asks the API to revoke the access token and returns to login`.
3. Un 401 `token_invalid` en una llamada autenticada posterior deja el login. Prueba `shows login when a later request rejects the access token`.
4. Si el POST de logout falla en la red, se ve el aviso, `koi_logged_out` queda `pending`, la sesión en memoria queda vacía y no hay un rechazo sin manejar. Prueba `warns, keeps the logged-out marker, and does not reject`.
5. Un 500 de logout conserva el camino de W1-45. El aviso, el marcador `pending` y el login se mantienen al recargar. Pruebas `journey: logout failure stays logged out after reload and /app/uso` y `journey: msw logout failure still returns to login`.

## No tocar

- `packages/contracts/**` y el OpenAPI publicado.
- Firmas de `app/commands/*` fuera de lo que este CCR ya cambió en la rama.
- El texto del aviso y los valores `pending` y `settled` del marcador.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

`docs/statechart/level2/auth-session.md` (A7, A13, A14, A15) y el PR #166.

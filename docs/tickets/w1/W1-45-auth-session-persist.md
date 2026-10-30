---
id: W1-45
workstream: W1
persona: Carlos
estado: en-curso
rama: w1-auth-session-persist
epica: E1-03
sprint: S4
pr:
depends_on: W1-15 W3-02
---

# [W1-45] Recargar conserva la sesión

## Qué se ve

Recargar el navegador deja al usuario en la misma pantalla, con la sesión abierta. El refresh vive en la cookie httpOnly `koi_refresh` que el login ya escribe. El arranque llama `POST /auth/refresh` en silencio y luego `GET /me`. Si el refresh falla, la sesión se cierra y aparece el login. Cerrar sesión llama `POST /auth/logout` y revoca ese refresh.

## Entradas ya decididas (no se cambian)

- Cookie `koi_refresh`, httpOnly, SameSite=lax, path `/api/v1` (W3-02). El cuerpo de `POST /auth/refresh` sigue siendo `RefreshTokenRequest` cuando el cliente lo envía.
- El access token sigue en memoria. No va a `localStorage` ni a `sessionStorage`.
- Transiciones A6 y A8 de `docs/statechart/level2/auth-session.md`, y J3 de `docs/statechart/ponds.md`.
- Un refresh rechazado responde 401 y borra la cookie. El JWT de acceso no se revoca al instante (eso es r6-7).
- Depends on W1-15 y W3-02, ambos hechos.

## Criterios de aceptación

1. Con la cookie vigente y sin token en memoria, recargar deja la lista de ponds en pantalla. Prueba `journey: reload keeps session`.
2. Si `POST /auth/refresh` falla, el arranque termina en el login y la sesión queda vacía. Prueba `journey: reload refresh failure logs out`.
3. Un access token vencido se renueva en silencio usando la cookie, sin mandar el refresh en el cuerpo. Prueba `auth: expired access refreshes silently`.
4. Cerrar sesión llama `POST /auth/logout` con el bearer y vuelve al login. Prueba `journey: logout returns to login`.
5. `POST /auth/refresh` sin cuerpo, solo con la cookie, rota el refresh y actualiza la cookie. Un cookie ya gastado responde 401 y la borra. Prueba `test_refresh_cookie_restores_session_and_clears_on_failure`.

## No tocar

- Firmas de `app/commands/*`.
- Tablas, columnas y enums.
- El schema publicado de `RefreshTokenRequest` (el cuerpo sigue siendo obligatorio en OpenAPI).
- r6-7 (revocar el access token al salir o al suspender).

## Si algo falta

Respondé `BLOQUEADO` solo si hay que *editar* OpenAPI o la firma de un comando. La cookie ya existe. Llamá `rotate_refresh`.

## Referencia

`docs/statechart/level2/auth-session.md` (A6, A8) y `docs/tickets/w3/W3-02-login-sesion.md`.

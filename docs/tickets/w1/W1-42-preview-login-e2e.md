---
id: W1-42
workstream: W1
persona: Carlos
estado: hecho
rama: w1-preview-login-gate
epica: E4-04
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/159"
depends_on: W1-40
---

# [W1-42] Regresión e2e del login en Preview

## Qué se ve

En el Preview de Vercel, `POST /api/v1/auth/login` responde JSON del API. Una contraseña incorrecta devuelve HTTP 401 con `code` igual a `invalid_credentials`. No devuelve 405 y no devuelve el HTML de la SPA. Con el administrador del gate, el mismo POST devuelve HTTP 200 y la interfaz queda en `/app`.

La medición hecha antes de este ticket es que el Preview fresco del tip de `main` `e45add8` ya devuelve 401 JSON ante una contraseña incorrecta. El ruteo ya funciona. Este ticket agrega la regresión e2e para que un Preview posterior no vuelva a servir `app.html` en esa ruta.

## Entradas ya decididas (no se cambian)

- La suite vive en `e2e/preview-login/`.
- `@playwright/test` queda en 1.56.1. `@axe-core/playwright` acompaña esa versión.
- El origen sale de `PLAYWRIGHT_BASE_URL`. Si esa variable falta, sale de `KOI_PUBLIC_BASE_URL`. Si ninguna está definida, el default es el Preview de la rama `w1-preview-login-gate`. Un origen localhost se rechaza.
- El caso feliz lee `KOI_GATE_ADMIN_EMAIL` y `KOI_GATE_ADMIN_PASSWORD`. Esos valores no se escriben en el repo y no se imprimen.
- Etiquetas de la pantalla de login. Correo, Contraseña, Iniciar sesión.
- `/login` no tiene un diálogo. Escape se comprueba sobre el formulario. El foco queda en un control del formulario y la URL sigue en `/login`.
- Depends on W1-40 landed. La suite llama al Preview. No reescribe `vercel.json` ni el cliente.

## Criterios de aceptación

1. Contraseña incorrecta. `POST /api/v1/auth/login` contra el origen del Preview devuelve 401, `content-type` con `application/json` y `code` `invalid_credentials`. El cuerpo no es HTML.
2. Caso feliz. Con las dos variables de entorno, el POST devuelve 200 JSON y el navegador termina en `/app` con el encabezado Ponds. Si falta una variable, ese test falla y pide definirlas. El caso de contraseña incorrecta corre igual.
3. En `/login`, Escape deja el foco en un control visible del formulario y la URL sigue en `/login`.
4. axe en 375, 768 y 1440 sobre `/login`. Tras el login feliz, axe en los mismos anchos sobre `/app`.
5. `fullyParallel` es true. Cada test usa su propio contexto. Las capturas quedan en `e2e/preview-login/artifacts/`, ignoradas por git. Si el login feliz corre, las mismas capturas se copian a `/opt/cursor/artifacts/preview-login/`.
6. Este cambio no edita código de producción en `apps/web`.

## No tocar

`apps/web/src/**`, `apps/web/vercel.json`, `apps/api/**`, `packages/contracts/**`, OpenAPI, firmas de comandos, secretos en el commit o en el cuerpo del PR.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

`e2e/pond-lifecycle/` para el layout de Playwright. W1-40 y el Preview del tip `e45add8` para el ruteo de `/api`. `apps/web/src/features/auth/login-page.tsx` para las etiquetas.

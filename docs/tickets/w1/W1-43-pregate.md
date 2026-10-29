---
id: W1-43
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-pregate
epica: E10-01
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/160"
depends_on:
---

# [W1-43] Pregate de lint, guardias, unitarias y e2e

## Qué se ve

En la raíz del repo, `npm run pregate` corre una sola secuencia y se detiene en el primer fallo. El log nombra el paso, repite la salida del hijo con prefijo y lista los pasos que no arrancaron. El mismo comando corre en el job `pregate` de CI.

La secuencia es: pruebas del runner, instalación web, lint web, `python3 scripts/agent_guards.py tree`, pruebas unitarias web, instalación de las tres suites Playwright, Chromium una vez, y en paralelo pond-lifecycle (puerto 5173), preview-login y dialog-viewport (puerto 5174).

Cada diálogo abierto en dialog-viewport, en 375, 768 y 1440 cuando ese diálogo existe, tiene rol dialog y nombre accesible, axe con `color-contrast` en passes, se cierra con Escape y devuelve el foco. La hoja del menú solo existe en 375.

## Entradas ya decididas (no se cambian)

- El plan vive en `scripts/pregate/plan.json`. Hay un solo grupo paralelo.
- `e2e/dialog-viewport/tests/dialogs.spec.ts` queda congelado desde el commit rojo.
- preview-login no lleva filtro `--grep`. Hereda `KOI_GATE_ADMIN_EMAIL` y `KOI_GATE_ADMIN_PASSWORD` si existen. El log dice si están definidas y no imprime los valores.
- El runner quita `VITE_ENABLE_MOCKS` y `VERCEL_ENV` del entorno de cada hijo.
- `PLAYWRIGHT_BASE_URL` no se define en el job. El default de preview-login sigue siendo el Preview de `w1-preview-login-gate`.
- Los jobs `web`, `guards` y `e2e-pond-lifecycle` se quedan.
- `depends_on` queda vacío. W1-42 ya está en la rama padre. Este PR no lo marca hecho.

## Criterios de aceptación

1. `npm run pregate` en la raíz sale 0 cuando lint, guardias tree, unitarias y las tres suites e2e pasan.
2. Un paso serial que falla no arranca los siguientes. El log dice `pregate fail` con el id y el código, y `pregate skipped` con los ids posteriores.
3. El grupo paralelo espera a los tres miembros. Si uno falla, el exit del grupo es 1 y el log marca pass o fail de cada miembro.
4. dialog-viewport cubre restore, suspend, reactivate, checkout, confirm, la hoja en 375 y la ausencia de hoja en 768 y 1440. Escape y foco siguen la tabla del plan. axe incluye `color-contrast` en passes, y un incomplete de esa regla falla el test.
5. El job `pregate` de CI ejecuta `npm run pregate` con `GH_TOKEN` y los secretos de admin. No define `VITE_ENABLE_MOCKS`, `VERCEL_ENV` ni `PLAYWRIGHT_BASE_URL`.
6. Una URL de preview que no es https, que apunta a localhost, o cuyo host no termina en `.vercel.app`, rechaza el plan antes de lanzar suites.
7. La salida no contiene el correo ni la contraseña del admin del gate.

## No tocar

Producción de Vercel. `VITE_ENABLE_MOCKS` en Production. `packages/contracts/**`, `apps/web/src/api/schema.d.ts`, firmas de `app/commands/*`. No borrar los jobs `web`, `guards` ni `e2e-pond-lifecycle`. No editar `e2e/dialog-viewport/tests/dialogs.spec.ts` después del commit rojo. No imprimir secretos.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

`e2e/pond-lifecycle/` y `e2e/preview-login/` para las suites que el plan reutiliza. `docs/tickets/w1/W1-42-preview-login-e2e.md` para el default del Preview. `.github/workflows/ci.yml` para el job que se agrega al lado de los existentes.

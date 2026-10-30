---
id: W1-44
workstream: W1
persona: Carlos
estado: hecho
rama: w1-email-resend
epica: E1-01
sprint: S4
pr: "#161"
depends_on: W3-05
---

# [W1-44] Proveedor de correo Resend (prod) con consola por defecto

## Qué se ve

Con `EMAIL_PROVIDER=console` (default) el mailer sigue imprimiendo el correo completo
en stdout. Con `EMAIL_PROVIDER=resend` la API envía vía Resend usando `RESEND_API_KEY` y
`EMAIL_FROM`. Si falta alguna de esas variables en modo resend, el proceso falla al
arrancar. Los errores de la API de Resend se registran sin filtrar la API key.
`.env.example`, `infra/env/prod.env.example` y `docs/manual-tecnico.md` documentan las
tres variables y la verificación de dominio en resend.com.

## Entradas ya decididas (no se cambian)

- API pública del módulo: `send(template, to, context)` en
  `apps/api/app/modules/notifications/` (W3-05).
- IDs de plantilla congelados: `verify_email`, `reset_password`, `invoice_issued`,
  `subscription_canceled`.
- `EMAIL_PROVIDER` ya documentado como `console` (dev/CI) o `resend` (prod).
- Variables nuevas: `RESEND_API_KEY`, `EMAIL_FROM` (placeholders vacíos en ejemplos).
- HTTP cliente del monorepo: `httpx` (promover a dependencia de runtime de la API si
  hace falta; no añadir el SDK oficial de Resend salvo que el ticket lo nombre).
- Sin cambio de OpenAPI, firmas de `app/commands/*`, ni modelo de datos.
- No cablear aún auth→mailer si no está; este ticket es el proveedor detrás de `send()`.

## Criterios de aceptación

1. Con `EMAIL_PROVIDER` ausente o `console`, `send()` usa el proveedor consola (prueba).
2. Con `EMAIL_PROVIDER=resend` y sin `RESEND_API_KEY` o sin `EMAIL_FROM`, el arranque
   falla de inmediato (prueba).
3. Con resend bien configurado, `send()` hace el POST esperado a la API de Resend
   (HTTP mockeado) con from/to/subject/html/text (prueba).
4. Un error o timeout de Resend se propaga o se registra sin incluir el valor de
   `RESEND_API_KEY` en logs (prueba).
5. `.env.example` e `infra/env/prod.env.example` listan `RESEND_API_KEY` y `EMAIL_FROM`
   con placeholders. `docs/manual-tecnico.md` documenta ambas y los pasos de
   verificación de dominio en resend.com.
6. `make check-api` y `make check-web` pasan. No se editan las pruebas de este ticket
   para forzar el verde.

## No tocar

- `packages/contracts/**`, OpenAPI generado, `apps/web/src/api/schema.d.ts`.
- Firmas de `apps/api/app/commands/*`.
- Migraciones Alembic / `docs/architecture/data-model.md`.
- Despliegue a producción o valores reales de secretos.
- `AGENTS.md`, workflows de CI (salvo que un path de ownership lo exija; no aplica).

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Decisiones

- `send()` hace `httpx.post` bloqueante (hasta 2 × 10 s). Quien lo llame desde el
  event loop debe correrlo en un hilo (o pasar a `httpx.AsyncClient`) cuando auth
  lo cablee.

## Referencia

Imitá el PR de W3-05 (`notifications` + pruebas unitarias del proveedor consola):
misma carpeta de módulo, mismo estilo de pruebas, evidencia red→green en el PR.

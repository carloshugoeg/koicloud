---
id: W1-51
workstream: W1
persona: Carlos
estado: hecho
rama: w1-reset-email
epica: E1-04
sprint: S5
pr: "#239"
depends_on: W1-44 W3-05
---

# [W1-51] Forgot password envía reset_password y logos PNG públicos

## Qué se ve

`POST /auth/forgot` con un correo existente crea el token de reset **y** entrega
(o encola vía el gate `EMAIL_PROVIDER`) el correo `reset_password` con enlace
`https://<base>/reset?token=…`. Con un correo desconocido responde igual
`200 {"ok": true}` y no envía nada. Los correos `reset_password` y `verify_email`
muestran un logo PNG absoluto por HTTPS (servido desde `apps/web/public/koi/`),
no el host muerto `app.koicloud.dev`. La página web `/reset` ya consume `?token=`.

## Entradas ya decididas (no se cambian)

- Comando `send_reset_token` y firma congelada en `apps/api/app/commands/auth.py`.
- Plantilla `reset_password` ya registrada en `notifications/templates.py`.
- Gate `send(template, to, context)` + `EMAIL_PROVIDER=console|resend` (W1-44 / W3-05).
- Base de enlaces desde `KOICLOUD_DOMAIN` / `koicloud_domain` (mismo patrón que verify).
- Asset PNG existente: `apps/web/public/koi/koi-mark-32.png` (también en
  `https://koicloud-web.vercel.app/koi/koi-mark-32.png`).
- Ruta web `/reset?token=` ya implementada (W2-02).
- Sin OpenAPI nuevo, sin migración, sin secretos, sin deploy, sin cambios de infra/env.

## Criterios de aceptación

1. Forgot con correo conocido entrega exactamente un correo `reset_password` vía
   consola/fake provider, con enlace `/reset?token=` y logo `https…png`. Prueba
   `test_forgot_known_email_sends_one_reset_email_with_token_link_and_png_logo`.
2. Forgot con correo desconocido responde el mismo status y body, y no envía correo.
   Prueba `test_forgot_unknown_email_same_response_sends_nothing`.
3. El HTML de `verify_email` usa un logo PNG absoluto `https` (no `app.koicloud.dev`).
   Prueba `test_verify_email_logo_is_absolute_https_png`.
4. `make check-api` pasa. Las pruebas nuevas de la fase 1 no se editan para forzar verde.

## No tocar

- `packages/contracts/**`, OpenAPI, firmas de `app/commands/*`.
- Migraciones Alembic / `docs/architecture/data-model.md`.
- `.env.example`, `docker-compose.yml`, workflows, deploy.
- Secretos o envío real a Resend en CI.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.

## Referencia

`apps/api/app/commands/auth.py` (`send_reset_token`, `_deliver_verify_email`),
`apps/api/app/modules/notifications/templates.py`,
`apps/api/app/modules/auth/tests/test_verify_email_send.py`,
`docs/tickets/w2/W2-02-recuperar-password.md`.

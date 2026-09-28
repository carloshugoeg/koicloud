---
id: W3-05
workstream: W3
persona: Jousé
estado: abierto
rama: w3-correos
epica: "E1-01, E1-04, E8-03"
sprint: S3
pr:
depends_on: W3-01
---

# [W3-05] Módulo `notifications`: 4 plantillas y proveedor de consola

## Qué se ve

Módulo de notificaciones que valida contexto y renderiza correo HTML/txt con proveedor `console`. Lo visible al equipo es el log completo del correo y las plantillas en español listas para usarse.

## Entradas ya decididas (no se cambian)

- Ruta propia: `apps/api/app/modules/notifications/**`.
- API del módulo: `send(template, to, context)`.
- El proveedor `console` imprime asunto, destinatario y cuerpo completo, incluyendo URLs de verify/reset.
- IDs congelados (cuatro, ni uno más): `verify_email`, `reset_password`,
  `invoice_issued`, `subscription_canceled`.
- Asuntos: «Verificá tu correo» · «Restablecé tu contraseña» · «Tu factura de KoiCloud» ·
  «Cancelación programada».
- Cuerpo: HTML + txt en español. Verify/reset incluyen la URL completa que recibe `send()`.
- Contextos mínimos: `verify_email`/`reset_password` → `{url, email}`;
  `invoice_issued` → `{code, total}`; `subscription_canceled` → `{plan, ends_on}`.

## Criterios de aceptación

1. `send()` rechaza templates desconocidos o contexto incompleto.
2. Las cuatro plantillas de *Entradas* renderizan HTML y txt.
3. El proveedor `console` deja visible la URL completa en verify/reset.
4. Hay una prueba unitaria feliz por plantilla y una de validación fallida.

## No tocar

- `apps/api/app/core/**`.
- `apps/api/app/commands/**`.
- `apps/api/alembic/**`.
- `apps/api/app/modules/{ponds,jobs,nodes,backups,metering,agent_access}/**`.
- `packages/contracts/**`.

## Si algo falta

Respondé `BLOQUEADO` solo si hace falta un quinto template o un campo fuera de *Entradas*.
Los cuatro IDs ya están en este ticket. No esperes otro freeze de W1.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

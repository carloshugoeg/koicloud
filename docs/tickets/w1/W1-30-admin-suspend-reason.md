---
id: W1-30
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-admin-suspend-reason
epica: E8-01
sprint: S4
pr: https://github.com/carloshugoeg/koicloud/pull/121
depends_on:
ccr: https://github.com/carloshugoeg/koicloud/issues/125
---

# [W1-30] Motivo de suspensión en bitácora + `user_not_found`

CCR [#125](https://github.com/carloshugoeg/koicloud/issues/125) aprobado por Carlos Hugo Escobar:

> Apruebo el cambio de contrato del motivo de suspensión en KoiCloud

## Qué se ve

`POST /api/v1/admin/users/{id}/suspend` acepta `reason` opcional (trim, max 500) y lo guarda
en `audit_events.metadata.reason`. Si el usuario no existe, responde `404` con
`code: user_not_found`. La UI envía el Motivo del diálogo y la bitácora lo muestra.

## Entradas ya decididas (no se cambian)

- Confirm textual `SUSPENDER` sin cambios.
- Columna `audit_events.metadata` jsonb existente (sin migración).
- Sin tocar `GET /plans`, `PlanOut` ni pricing (PR #123 / W1-27 no aprobados).
- Alcance del CCR #125: solo `reason` + `user_not_found`.

## Criterios de aceptación

1. Body tipado con `reason` opcional, trim, maxLength 500; OpenAPI regenerado.
2. Suspend con motivo escribe `metadata.reason` en `audit_events`.
3. Motivo ausente o solo espacios no mete la clave `reason` en metadata.
4. Usuario inexistente → `404` + `user_not_found` (no `internal_error`).
5. Pruebas API cubren (2)–(4) y el límite de 500 caracteres.
6. Diálogo Motivo en desktop y 375 px con capturas en el PR.

## No tocar

- `GET /plans`, schemas de planes, pricing.
- Migraciones Alembic.
- Firmas de comandos ajenos a admin suspend/reactivate.

## Si algo falta

Respondé `BLOQUEADO: requiere CCR porque …` y pará.

## Referencia

CCR #66 + G1 ticket (`docs/tickets/w1/G1-billing-persistence.md`) para el patrón
CCR issue + ticket + `make contracts` + CHANGELOG.

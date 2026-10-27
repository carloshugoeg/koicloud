---
id: W1-32
workstream: W1
persona: Carlos
estado: en_revision
rama: w1-admin-subscriptions
epica: "E8-02"
sprint: S4
pr: https://github.com/carloshugoeg/koicloud/pull/132
depends_on:
---

# [W1-32] Admin subscriptions (#96 A7 / residual W2-10)

## Qué se ve

`/app/admin/subscriptions` deja de ser placeholder. Una tabla densa lista las
suscripciones del sistema (email del dueño, plan, estado, periodo) vía
`GET /api/v1/admin/subscriptions`. Sin koi. Guard `admin_only` igual que el resto del panel.

## Entradas ya decididas (no se cambian)

- **CCR aprobado:** [#128](https://github.com/carloshugoeg/koicloud/issues/128) (amendment r3 /
  issue [#96](https://github.com/carloshugoeg/koicloud/issues/96) comment 6445716121).
- Amendment: issue [#96](https://github.com/carloshugoeg/koicloud/issues/96) A7 (risk high / money).
- W2-10 marcó `hecho` las tres tablas; esta ruta quedó placeholder a propósito (sin endpoint).
- `AdminSubscriptionOut` + `admin_list_subscriptions` + pantalla + MSW + tests.
- Paginación por cursor, sin filtros de query en v0 (precedente W3-12 ponds/audit).
- **ID uniqueness:** W1-28 es [#124](https://github.com/carloshugoeg/koicloud/pull/124)
  retention; W1-30 es [#121](https://github.com/carloshugoeg/koicloud/pull/121) suspend;
  W1-31 es NIT checkout. Este ticket es **W1-32** (ex borrador W1-29 en #129).
- **No tocar** PR [#121](https://github.com/carloshugoeg/koicloud/pull/121) (suspend reason /
  CCR #125). Solo anotar dependencia si el panel comparte hooks; no duplicar motivo.
- **No tocar** PR [#123](https://github.com/carloshugoeg/koicloud/pull/123) PlanOut.
- Autor: Carlos Hugo Escobar. Sin merge hasta «Carlos yes».

## Criterios de aceptación

1. `GET /admin/subscriptions` (admin) devuelve lista tipada con `user_email` + campos de sub.
2. No-admin recibe `admin_only`.
3. La página reemplaza `PlaceholderPage`; loading / vacío / error presentes.
4. Tabla densa (filas ~40 px, `tabular-nums` donde aplique); sin koi.
5. Pruebas API + render/interacción web.
6. Proof embebido en el PR body. PR **abierto** (no merge).

## No tocar

- PR #121 / CCR #125 (no reimplementar motivo de suspensión).
- PR #123 PlanOut.
- Mutaciones admin sobre suscripciones (fuera de alcance de este ticket).
- `src/api/schema.d.ts` a mano (solo vía `make contracts` tras CCR).

## Si algo falta

`BLOQUEADO: requiere CCR porque no existe GET /admin/subscriptions` — ver #128.
No inventes el path ni el schema.

## Referencia

Imitá el panel de [#85](https://github.com/carloshugoeg/koicloud/pull/85) (W2-10) y el
cierre money/open de [#123](https://github.com/carloshugoeg/koicloud/pull/123).

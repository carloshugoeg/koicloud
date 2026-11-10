---
id: W1-49
workstream: W1
persona: Carlos
estado: hecho
rama: w1-account-page
epica: "E1-05"
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/235"
depends_on:
---

# [W1-49] Pantalla Cuenta (perfil + cambio de contraseña)

## Qué se ve

`/app/account` muestra nombre y NIT editables, y un formulario de cambio de
contraseña (actual, nueva, confirmar). Ya no aparece el scaffold E1-05.

## Entradas ya decididas (no se cambian)

- `GET /me` y `PATCH /me` ya existen (`get_me`, `update_profile`).
- Nuevo endpoint mínimo: `POST /me/change-password` → `204`.
- Errores: `invalid_credentials`, `password_too_weak`.
- Sin migración. Sin delete-me ni resend en este ticket.
- MSW cubre preview. Textos en español.

## Criterios de aceptación

1. La página renderiza nombre y NIT del usuario autenticado.
2. Guardar cambios llama `PATCH /me` y muestra confirmación.
3. Si nueva ≠ confirmar, error de cliente sin llamar a la API.
4. Cambio exitoso llama `POST /me/change-password` y muestra éxito.
5. Errores de API (`invalid_credentials`) se muestran con `code`.
6. No queda copy de scaffold (`Listo para conectar`, `Próximo paso`, etc.).

## No tocar

- Migraciones Alembic.
- Soft-delete / `DELETE /me`.
- Infra, env, deploys.

## Si algo falta

`BLOQUEADO` solo si hace falta una migración o un CCR fuera de este endpoint.

## Referencia

Slim de #148 (`w1-account-e105`) sin delete/resend.

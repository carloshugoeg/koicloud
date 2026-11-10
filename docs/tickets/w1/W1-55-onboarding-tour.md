---
id: W1-55
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-onboarding-tour
epica: "demo-P1"
sprint: S4
pr:
depends_on: W1-49
---

# [W1-55] Recorrido de onboarding y toasts de acciones

Demo P1 (11 nov). Tour introductorio + feedback de mutaciones en la Web.

## Qué se ve

Tras el primer login al shell, el usuario ve 3 tarjetas centradas y luego
coachmarks sobre la barra lateral: «Aquí ves tus ponds», «Aquí ves tus planes»
(sobre Uso y facturación) y «Aquí ves tu cuenta» (Perfil). Puede omitir; el
hecho queda en `localStorage` por `user.id`. En Cuenta, «Volver a ver el
recorrido» lo reinicia. Las acciones crear/eliminar pond, contratar plan y
guardar perfil/contraseña muestran toast de éxito; los errores de API usan el
catálogo vía `problemToMessage`. Listados de ponds, planes y cuenta tienen
cargando / vacío / error.

## Entradas ya decididas (no se cambian)

- Persistencia cliente: clave `koicloud:intro-tour-v1:<userId>` = `done`.
- Sin flag de servidor ni cambios en `apps/api`.
- Toast host ya montado (`lib/toast` + `ToastHost`).
- Nav real: Ponds, Uso y facturación (planes), Perfil (cuenta). No añadir ítem
  «Planes» al sidebar (consolidado en `/app/uso`).
- No tocar signup, first-login plan chooser (`w1-plan-onboarding`), ni
  auth/notifications API. No editar CI ni `check_ownership.py`.
- Piel: `docs/visual-guidelines.md`.

## Criterios de aceptación

1. El tour aparece una vez por usuario si no hay `done` en storage.
2. Omitir persiste `done` y no vuelve a mostrar el tour al recargar el shell.
3. Cuenta ofrece replay que limpia `done` y reabre el tour.
4. Coachmarks apuntan a nodos con `data-tour-target` ponds / plans / account.
5. Crear pond con error de API muestra toast con mensaje del catálogo.
6. Toasts de éxito en create/delete pond, plan contratado, perfil y contraseña.
7. `make check-web` pasa.

## No tocar

- `apps/api/**` (auth, notifications, commands).
- Signup / registro / first-login plans onboarding (`w1-plan-onboarding`).
- `.github/scripts/check_ownership.py` y workflows de CI.
- OpenAPI / migraciones.

## Si algo falta

`BLOQUEADO` solo si hay que editar un contrato congelado o un archivo ajeno.
Si el comando o el toast host ya existen, úsalos.

## Referencia

Patrón de toast en `features/ponds/backups-page.tsx` y Cuenta en W1-49 (#235).

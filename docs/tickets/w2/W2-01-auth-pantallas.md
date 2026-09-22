---
id: W2-01
workstream: W2
persona: Jason
estado: abierto
rama: w2-auth-pantallas
epica: "E1-01, E1-02, E1-03"
sprint: S2
pr:
---

# [W2-01] Registro, login y verificación de correo

## Qué se ve

Flujo de auth del mockup `#auth`: registro -> estado «Revisa tu correo» -> verificación por token -> login -> entrada a `/app`. La vista usa la composición de dos columnas de `docs/visual-guidelines.md` §10 fila 1, con panel del estanque al lado izquierdo y formulario centrado sobre `bone`.

## Entradas ya decididas (no se cambian)

- Rutas: `/registro`, `/login`, `/verificar?token=`.
- API: `POST /auth/register`, `POST /auth/verify`, `POST /auth/login`.
- Campos de registro: `full_name`, `email`, `password`, `nit` opcional.
- Login responde `{access_token, refresh_token, user}`; verify responde `{user_id, email_verified:true}`.
- Códigos de error: `email_taken`, `password_too_weak`, `invalid_credentials`, `email_not_verified`, `token_invalid`, `token_expired`, `rate_limited`.
- Piel y copy: textos del mockup; sin `dark:`, sin `Inter`, sin hex fuera de los tokens.

## Criterios de aceptación

1. Registro exitoso muestra el copy de verificación de 24 h y no hace login implícito.
2. Verificación válida consume el token y lleva al siguiente paso del flujo de auth.
3. Verificación inválida o expirada muestra mensaje por `code`, sin traza.
4. Login guarda la sesión y redirige a `next` o `/app`.
5. Pruebas de render + interacción cubren registro, verificación y login.
6. La vista es usable a 360 px y mantiene foco visible en todos los campos.

## No tocar

- `src/api/client.ts`.
- `src/api/schema.d.ts`.
- `src/lib/auth-store.ts`.
- `src/app/router.tsx` (si hiciera falta una ruta nueva, se pide a W1).
- `src/components/ui/*` salvo cambios de tema cuando el ticket lo permita.
- Cualquier archivo fuera de `apps/web/`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes endpoints, campos, hooks, rutas ni códigos de error.
- W1 congela los nombres exactos de los hooks de auth y el registro de estas rutas en Fase 0; si no existen cuando tomes el ticket, bloqueá en vez de inventarlos.

## Referencia

Este ticket produce el PR #1 de referencia. Al cerrarlo, su PR debe quedar como molde de estructura, pruebas y plantilla para los demás tickets.

---
id: W2-02
workstream: W2
persona: Jason
estado: en-revision
rama: w2-recuperar-password
epica: "E1-04"
sprint: S3
pr: "https://github.com/carloshugoeg/koicloud/pull/24"
depends_on:
---

# [W2-02] Recuperación de contraseña

## Qué se ve

Flujo del mockup `#auth` para `¿Olvidaste tu contraseña?`: formulario de solicitud, confirmación neutral y pantalla de restablecimiento con token. Reusa la misma piel de dos columnas de auth definida en `docs/visual-guidelines.md` §10 fila 1.

## Entradas ya decididas (no se cambian)

- Rutas ya registradas en `src/app/router.tsx`: `/forgot` y `/reset?token=`.
  Implementá `ForgotPage` y `ResetPage`. No pidas CCR por el router.
- API: `POST /auth/forgot` y `POST /auth/reset`. Los hooks/cliente de Fase 0 ya existen.
- Forgot siempre devuelve `202 {ok:true}` con mensaje neutral, exista o no el correo.
- Reset consume un token de un solo uso con TTL de 1 h y acepta la nueva contraseña.
- Códigos de error: `token_invalid`, `token_expired`, `password_too_weak`, `rate_limited`.
- Textos y layout siguen el mismo patrón visual del ticket W2-01.

## Criterios de aceptación

1. La pantalla de forgot siempre muestra confirmación neutral y no filtra existencia del correo.
2. Reset exitoso consume el token una sola vez y muestra el estado final esperado.
3. Password débil se muestra inline desde `code`, no desde copy libre.
4. Token expirado o inválido ofrece salida clara para reintentar el flujo.
5. Pruebas de render + interacción cubren forgot, reset feliz y token expirado.

## No tocar

- `src/api/client.ts`.
- `src/api/schema.d.ts`.
- `src/lib/auth-store.ts`.
- `src/app/router.tsx` (las rutas `/forgot` y `/reset` ya están).
- `src/components/ui/*` salvo cambios de tema cuando el ticket lo permita.
- Cualquier archivo fuera de `apps/web/`.

## Si algo falta

Respondé `BLOQUEADO` solo si hay que *editar* OpenAPI o inventar un endpoint.
`/forgot` y `/reset` ya están en el router. No declares BLOQUEADO por hooks.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

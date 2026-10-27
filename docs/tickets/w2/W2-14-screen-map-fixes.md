---
id: W2-14
workstream: W2
persona: Jason
estado: hecho
rama: w2-screen-map-fixes
epica: "E1-01"
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/122"
depends_on:
---

# [W2-14] Ajustes del screen map: password, plan y detalle

## Qué se ve

Tres correcciones de la sección 5 del screen map / plano:

1. Registro y restablecer contraseña muestran el mismo mínimo de **10** caracteres, leído de una sola constante compartida.
2. Crear pond muestra el plan real de la suscripción del usuario (`GET /me` + catálogo de planes), no un «Micro» fijo.
3. El detalle del pond se actualiza solo mientras el estado es transitorio (poll), y muestra paneles de **en curso** y **con fallas**.

## Entradas ya decididas (no se cambian)

- Rutas ya montadas: `/register`, `/reset`, `/app/ponds/new`, `/app/ponds/:id`.
- Hooks: `useRegisterMutation`, `useResetPasswordMutation`, `usePlansQuery`, `useGetPond`, y `GET /api/v1/me` vía cliente OpenAPI.
- Constante compartida en `apps/web/src/lib/password.ts` (`MIN_PASSWORD_LENGTH = 10`).
- Estados transitorios de pond: `pending`, `provisioning`, `restoring`, `deleting`; poll cada 4 s como el listado.
- Sin editar OpenAPI ni el mínimo del backend (sigue en 8 en contrato).
- Sin tocar copy de precios ni de planes.
- Piel: `docs/visual-guidelines.md` (tira de aprovisionamiento permitida en detalle).

## Criterios de aceptación

1. Register y reset muestran «Mínimo 10 caracteres» (o el texto derivado de la misma constante) y ambos inputs usan `minLength` de esa constante. Prueba: `src/lib/password.test.ts` y el caso screen-map en `auth.test.tsx`.
2. Crear pond, con suscripción activa distinta de Micro en `GET /me`, muestra ese plan (p. ej. «Pro · heredado de tu suscripción») y no «Micro» hardcodeado. Prueba: `create.test.tsx`.
3. Detalle del pond: con `observed_state` transitorio hace poll hasta estado terminal; muestra panel in-progress en aprovisionamiento y panel failed con `last_error` cuando falla. Prueba: `detail.test.tsx`.

## No tocar

- `apps/web/src/api/client.ts`
- `apps/web/src/api/schema.d.ts`
- `apps/web/src/lib/auth-store.ts`
- `apps/web/src/components/ui/*`
- Cualquier archivo fuera de `apps/web/` salvo este ticket en `docs/tickets/w2/**`
- Precios, textos de catálogo de planes, OpenAPI / firmas de comandos

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

Imitá el PR #57 (`[W2-06] Detalle del pond`) y el #24 (`[W2-02] Recuperar password`): misma estructura de archivos, mismo estilo de pruebas MSW + Testing Library.

---
id: W2-12
workstream: W2
persona: Jason
estado: abierto
rama: w2-tema-y-estados
epica: "RNF-08"
sprint: S4
pr:
---

# [W2-12] Layout, tema, estados vacíos y responsive a 360 px

## Qué se ve

Shell base de la SPA, tokens visuales, estados de datos consistentes y navegación usable a 360 px. Este ticket pule la piel transversal definida en `docs/visual-guidelines.md`, no abre nuevas superficies.

## Entradas ya decididas (no se cambian)

- Alcance: `AppLayout`, `Sidebar`, `Header`, `PageHeader`, `PondStatusBadge`, `DataState` y tokens de `index.css`.
- Las reglas mandan desde `docs/visual-guidelines.md` §5.1, §6.2 y §11.2.
- Todo listado tiene tres estados: cargando, vacío con CTA y error con `Reintentar`.
- La suspensión es un banner global de cuenta, no un badge dentro del pond.
- No hay dark mode, no hay `Inter` y no hay hex fuera de `index.css`.
- `src/components/ui/*` solo se toca para el puente de tema.

## Criterios de aceptación

1. La sidebar respeta grupos, activos y colapso definidos por la guía visual.
2. No quedan hex literales fuera de `index.css` ni clases `dark:` nuevas.
3. 404, arranque de sesión y listados reutilizan el mismo patrón de `DataState`.
4. El foco visible y la navegación por teclado funcionan en el shell.
5. La app es usable a 360 px sin scroll horizontal.
6. La accesibilidad medida en `/`, `/app` y `/app/ponds/:id` queda en 90 o más.

## No tocar

- `src/api/client.ts`.
- `src/api/schema.d.ts`.
- `src/lib/auth-store.ts`.
- `src/app/router.tsx` salvo una ruta que este ticket nombre y aún no exista. Las de Fase 0 ya están.
- `src/components/ui/*` salvo cambios de tema cuando el ticket lo permita.
- Cualquier archivo fuera de `apps/web/`.

## Si algo falta

Respondé `BLOQUEADO` solo si el shell o los tokens de `index.css` no están en `main`.
El scaffold de Fase 0 ya está. No lo rehagas.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

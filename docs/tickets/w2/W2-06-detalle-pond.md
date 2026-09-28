---
id: W2-06
workstream: W2
persona: Jason
estado: abierto
rama: w2-detalle-pond
epica: "E3-03"
sprint: S3
pr:
---

# [W2-06] Detalle del pond y cadena de conexión

## Qué se ve

Pantalla que replica el mockup `#detalle-pond` y `#conexion`: cabecera con nombre del pond y badge de estado, más tarjeta de conexión con host, puerto, usuario, base, contraseña enmascarada y URI completa con `Revelar` y `Copiar URI`.

## Entradas ya decididas (no se cambian)

- Ruta: `/app/ponds/:id` en `src/app/router.tsx` (ya registrada).
- Datos: `useGetPond(id)` y `useGetConnection(id)` en `src/api/hooks/ponds.ts`.
- Tipos: `components['schemas']['Pond']` y `components['schemas']['Connection']` de `src/api/schema.d.ts`.
- Errores a manejar por `code`: `pond_not_found` (404) y `not_owner` (403).
- Textos en español tomados del mockup; el texto visible viene de `problemToMessage` cuando sea error.
- Piel: `docs/visual-guidelines.md` §10 filas 5 y 5b; URI y snippets en IBM Plex Mono sobre `paper`.

## Criterios de aceptación

1. Con el handler MSW `pond-running`, se ven los cinco campos de conexión y el badge dice `En línea`.
2. La contraseña se muestra como `••••••••` hasta pulsar `Revelar`, y no está en el DOM antes de ese clic.
3. `Copiar URI` deja la URI en el portapapeles con mock de `navigator.clipboard`.
4. Con el handler `pond-not-found`, se ve el mensaje del catálogo y no una traza.
5. Los estados cargando, vacío y error están presentes en la vista.
6. La página queda en verde con `make check-web` y sin `any` nuevos.
7. Hay prueba de render y prueba de interacción en `src/features/ponds/__tests__/`.

## No tocar

- `src/api/client.ts`.
- `src/api/schema.d.ts`.
- `src/lib/auth-store.ts`.
- `src/app/router.tsx` salvo una ruta que este ticket nombre y aún no exista. Las de Fase 0 ya están.
- `src/components/ui/*` salvo cambios de tema cuando el ticket lo permita.
- Cualquier archivo fuera de `apps/web/`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para W1> porque <razón>` y pará.
No inventes endpoints, campos, hooks, rutas ni códigos de error.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

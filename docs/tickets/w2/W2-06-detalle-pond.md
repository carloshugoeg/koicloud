---
id: W2-06
workstream: W2
persona: Jason
estado: abierto
rama: w2-detalle-pond
epica: E3-03
sprint: S3
pr:
---

# [W2-06] Detalle del pond y cadena de conexión

## Qué se ve

Pantalla que replica el mockup §5 y §5b
(`docs/entrega-2/mockups/pantallas-principales.html`): cabecera con nombre del pond y badge
de estado, y una tarjeta de conexión con host, puerto, usuario, nombre de la base,
contraseña enmascarada y URI completa, con botón «Revelar» y botón «Copiar URI».

## Entradas ya decididas (no se cambian)

- Ruta: `/app/ponds/:id` en `src/app/router.tsx` (ya registrada).
- Datos: `useGetPond(id)` y `useGetConnection(id)` en `src/api/hooks/ponds.ts` (ya existen).
- Tipos: `components['schemas']['Pond']` y `['Connection']` de `src/api/schema.d.ts`.
- Errores a manejar por `code`: `pond_not_found` (404), `not_owner` (403). El texto en
  español sale de `problemToMessage` en `src/lib/errors.ts`; no escribas mensajes nuevos.
- Textos en español, tomados literal del mockup.
- Piel: `docs/visual-guidelines.md` §10 filas 5 y 5b. El mockup da los campos, no los
  colores. Solo tokens de `index.css`; sin `dark:`, sin `Inter`, sin hex literales. La URI y
  los snippets van en IBM Plex Mono sobre `paper`; el badge de estado sale de §6.2.

## Criterios de aceptación

1. Con el handler MSW `pond-running`, se ven los cinco campos de conexión y el badge dice
   «En línea» con su glifo `●`.
2. La contraseña se muestra como `••••••••` hasta pulsar «Revelar», y no está en el DOM
   antes de ese clic.
3. «Copiar URI» deja la URI en el portapapeles (probado con mock de `navigator.clipboard`) y
   el icono cambia a `✓` por 1.2 s.
4. Con el handler `pond-not-found`, se ve el mensaje del catálogo, no una traza.
5. Los tres estados del cargado están presentes: skeleton, vacío y error con «Reintentar».
6. Página ≤ 250 líneas, sin `any`, `make check-web` en verde.
7. Prueba de render + prueba de interacción en `src/features/ponds/__tests__/`.

## No tocar

`src/api/client.ts` · `src/api/schema.d.ts` · `src/lib/auth-store.ts` · `src/app/router.tsx`
(si hace falta una ruta nueva, se pide) · `src/components/ui/*` salvo tema · cualquier
archivo fuera de `apps/web/`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

Imitá el PR de `[W2-01] Pantalla de registro y login`: misma estructura de archivos, mismo
estilo de pruebas, misma forma de llenar la plantilla de PR.

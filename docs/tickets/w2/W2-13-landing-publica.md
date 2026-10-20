---
id: W2-13
workstream: W2
persona: Jousé
estado: en-revision
rama: w2-landing-publica
epica: "E2-01"
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/89"
---

# [W2-13] Landing pública y catálogo de planes

**Dueño:** Jousé Menendez (`@Josh-JM`).

**Excepción cross-workstream (aprobada por Carlos):** aunque `apps/web/**` es superficie de W2
([`docs/WORKSTREAMS.md`](../../WORKSTREAMS.md) §2), Carlos autoriza a Jousé a implementar y
mantener **solo** la landing pública de este ticket en `apps/web`. La autorización no se
extiende a otras pantallas de la SPA ni a rutas fuera del alcance de abajo. El PR de
implementación es [#89](https://github.com/carloshugoeg/koicloud/pull/89) (abierto; este
ticket no lo declara hecho).

## Qué se ve

La página pública de producto en `/`: marca KoiCloud, hero editorial, panel del estanque
animado, catálogo de tres planes y la sección «Cómo funciona». Sustituye el placeholder de
Fase 0. Arquitectura de información:
[`docs/entrega-2/mockups/pantallas-principales.html#landing`](../../entrega-2/mockups/pantallas-principales.html#landing)
(Pantalla 0 · E2-01). Piel:
[`docs/visual-guidelines.md`](../../visual-guidelines.md) §10 fila 0.

Secciones obligatorias, en este orden:

1. **Barra pública** — marca KoiCloud, anclas a `#planes` y `#como-funciona`, CTAs a
   `/login` e `/register`.
2. **Hero** — título en Fraunces 56 px
   («Tu Postgres en línea antes de que se enfríe el café.»), lead, CTAs «Crear cuenta» y
   «Ver planes», facts `~40 s` / `3` superficies / `USD 5`, panel del estanque de 320 px con
   tres koi y paneo de agua.
3. **Planes** — tres tarjetas (Sandbox, Micro, Pro) con nombre, precio, vigencia y CTA.
   Micro destacado con borde 2 px `turquoise-700` y badge «Recomendado».
4. **Aviso de pago simulado** — texto visible de proyecto académico, sin cobro real.
5. **Cómo funciona** — tres pasos (Contratas un plan, Creas tu pond, Te conectas) con
   bandas ICG.

## Entradas ya decididas (no se cambian)

- Ruta: `/` (ya registrada en `src/app/router.tsx`).
- Feature bajo `src/features/landing/` (página + piezas; cada archivo de página ≤ 250 líneas).
- Datos de planes vía `usePlansQuery()` ya existente. Sin endpoints nuevos.
- Tokens y movimiento del estanque en `src/index.css` (`pond-water-hero`, paneo 72 s / tesela
  480 px según `visual-guidelines.md` §7.2). Sin hex literales fuera de `index.css`.
- Tema claro. Fuentes Fraunces + Instrument Sans. Sin dark mode y sin `Inter`.
- Textos de UI en español. Copy del hero y facts alineados al mockup citado.
- Rama de implementación: `w2-landing-publica` (prefijo W2 para el job `ownership` sobre
  `apps/web/**`).

## Criterios de aceptación

1. En `/` se ve el hero con el título display a 56 px, los tres facts y el estanque de
   320 px con tres koi animados (prueba de render + comprobación manual del paneo).
2. El catálogo muestra Sandbox, Micro y Pro conectados a `usePlansQuery()`. Micro lleva
   borde turquesa y badge «Recomendado».
3. El aviso de pago simulado (proyecto académico, sin cobro real) es visible en la página.
4. La sección «Cómo funciona» muestra los tres pasos con bandas superiores ICG.
5. La barra pública enlaza a `/login`, `/register`, `#planes` y `#como-funciona`.
6. `make check-web` pasa (lint, typecheck, tests, build) con prueba de render de la landing.

## No tocar

- Cualquier archivo fuera de `apps/web/` (API, contratos, CLI, infra, otros tickets).
- `src/api/client.ts`, `src/api/schema.d.ts`, `src/lib/auth-store.ts`.
- `src/components/ui/*`.
- `src/app/router.tsx` (la ruta `/` ya existe).
- Pantallas autenticadas (`/app/**`), checkout o contratación (W2-03 / flujo in-app).
- Módulos de W3 en `apps/api/app/modules/{auth,users,billing,notifications,admin}/**`.
- Contratos congelados (OpenAPI, errores, firmas de `commands/`, tablas, enums). Sin CCR.
- Otras features de `apps/web/src/features/*` que no sean `landing/`.
- En `src/index.css`, solo las reglas necesarias para el estanque hero. No rehacer el tema
  global (eso es W2-12).

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno a este alcance.
Si `usePlansQuery` o la ruta `/` ya existen, usalos. No inventes endpoints, campos ni
pantallas.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de
pruebas y misma forma de cerrar criterios en el PR. El PR de implementación de este ticket
es [#89](https://github.com/carloshugoeg/koicloud/pull/89).

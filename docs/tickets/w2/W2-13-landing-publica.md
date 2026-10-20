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
   «Ver planes», facts `~40 s` / `3` superficies / `USD 5`, y **debajo del titular** el
   panel del estanque a **100 % × 320 px** con tres koi y paneo de agua
   (`visual-guidelines.md` §7.3 y §10 fila 0). No va al lado del titular en ningún
   breakpoint.
3. **Planes** — tres tarjetas (Sandbox, Micro, Pro) cuyos límites, descripción y vigencia
   salen de `PlanOut`. Micro destacado con borde 2 px `turquoise-700` y badge
   «Recomendado». Estados cargando, vacío y error visibles.
4. **Aviso de pago simulado** — texto visible de proyecto académico, sin cobro real.
5. **Cómo funciona** — tres pasos (Contratas un plan, Creas tu pond, Te conectas) con
   bandas ICG.
6. **CTA sticky en móvil** — el CTA principal permanece fijo y usable en viewport estrecho.

## Entradas ya decididas (no se cambian)

- Ruta: `/` (ya registrada en `src/app/router.tsx`).
- Feature bajo `src/features/landing/` (página + piezas; cada archivo de página ≤ 250 líneas).
- Datos de planes vía `usePlansQuery()` ya existente. Campos de tarjeta desde `PlanOut`:
  `name`, `description`, `price_monthly_usd`, `max_ponds`, `max_storage_gb`,
  `validity_minutes`, `postpaid`. Sin endpoints nuevos. Sin catálogo `defaultPlans` con
  límites o textos duplicados a mano; local solo presentación (banda, destacado, CTA).
- Tokens y movimiento del estanque en `src/index.css` (`pond-water-hero`, paneo 72 s /
  tesela 480 px según `visual-guidelines.md` §7.2). En
  `@media (prefers-reduced-motion: reduce)`: `.pond-water-hero { animation: none; }` y
  koi estáticos (§7.5). Sin hex literales fuera de `index.css`.
- Meta: `apps/web/index.html` con título y descripción reales en español, Open Graph y
  Twitter Card, imagen 1200×630 en `apps/web/public/`.
- Prerender de `/` en el build. Dependencia nombrada (si hace falta añadirla):
  `vite-plugin-prerender`. Su alta en `package.json` / lockfile requiere decisión y
  aprobación de Carlos (W1 / CODEOWNERS). Sin otras dependencias nuevas.
- Tema claro. Fuentes Fraunces + Instrument Sans. Sin dark mode y sin `Inter`.
- Textos de UI en español. Copy del hero y facts alineados al mockup citado.
- Rama de implementación: `w2-landing-publica` (prefijo W2 para el job `ownership` sobre
  `apps/web/**`).

## Criterios de aceptación

1. En `/` el hero muestra el título display a 56 px, los tres facts y, **debajo del
   titular**, el panel del estanque a **100 % × 320 px** con tres koi (prueba de render +
   comprobación manual del paneo). No hay layout de dos columnas que ponga el estanque al
   lado del titular (`visual-guidelines.md` §7.3, §10 fila 0).
2. Con `prefers-reduced-motion: reduce`, `.pond-water-hero` y los koi quedan estáticos
   (`animation: none` en el media query de §7.5). Verificable con prueba o paso manual
   concreto.
3. El catálogo muestra Sandbox, Micro y Pro. Límites, descripción y vigencia vienen de
   `PlanOut` vía `usePlansQuery()` (sin `defaultPlans` con esos datos a mano). Micro lleva
   borde turquesa y badge «Recomendado». Hay estados cargando, vacío y error (AGENTS.md
   §5). Hay prueba MSW contra `GET /plans` que comprueba que las tarjetas reflejan la
   respuesta.
4. El aviso de pago simulado (proyecto académico, sin cobro real) es visible en la página.
5. La sección «Cómo funciona» muestra los tres pasos con bandas superiores ICG.
6. La barra pública enlaza a `/login`, `/register`, `#planes` y `#como-funciona`.
7. `apps/web/index.html` tiene título y descripción reales en español, más etiquetas
   Open Graph y Twitter con imagen 1200×630.
8. El build deja HTML prerenderizado de `/` con contenido visible sin ejecutar JS (no solo
   `<div id="root"></div>` vacío). Si se añade `vite-plugin-prerender`, el PR de
   implementación lo declara en «Decisiones» y espera la aprobación de Carlos.
9. En móvil hay un CTA principal sticky visible y usable.
10. Preview de Vercel (o equivalente) abre la landing **sin sesión**. Lighthouse móvil ≥ 95
    en las cuatro categorías; scores adjuntos o citados en el PR de implementación.
11. `make check-web` pasa (lint, typecheck, tests, build) con las pruebas de landing
    anteriores.

## No tocar

- Cualquier archivo fuera de `apps/web/`, **excepto**
  `docs/tickets/w2/W2-13-landing-publica.md` (actualizar `estado` / `pr` en la rama de
  implementación, según `docs/tickets/README.md` §2).
- `src/api/client.ts`, `src/api/schema.d.ts`, `src/lib/auth-store.ts`.
- `src/components/ui/*`.
- `src/app/router.tsx` (la ruta `/` ya existe).
- Pantallas autenticadas (`/app/**`), checkout o contratación (W2-03 / flujo in-app).
- Módulos de W3 en `apps/api/app/modules/{auth,users,billing,notifications,admin}/**`.
- Contratos congelados (OpenAPI, errores, firmas de `commands/`, tablas, enums). Sin CCR.
- Otras features de `apps/web/src/features/*` que no sean `landing/`.
- En `src/index.css`, solo las reglas del estanque hero y reduced-motion. No rehacer el
  tema global (eso es W2-12).
- Dependencias no nombradas en *Entradas*. `vite-plugin-prerender` solo con decisión de
  Carlos.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno a este alcance.
Si `usePlansQuery` o la ruta `/` ya existen, usalos. Si el prerender necesita la
dependencia nombrada, pedí la decisión de Carlos en el PR; no inventes otro paquete.
No inventes endpoints, campos ni pantallas.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de
pruebas y misma forma de cerrar criterios en el PR. El PR de implementación de este ticket
es [#89](https://github.com/carloshugoeg/koicloud/pull/89).

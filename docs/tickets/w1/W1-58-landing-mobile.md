---
id: W1-58
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-landing-mobile
epica: E2-01
sprint: S8
pr: https://github.com/carloshugoeg/koicloud/pull/253
depends_on:
---

# [W1-58] Landing mobile-first para la demo del 11 nov

## Qué se ve

1. La ruta pública `/` explica qué es KoiCloud arriba del fold en 375 px y 390 px:
   PostgreSQL 16 gestionado, agent-first, con CTA «Crear cuenta» visible sin scroll
   horizontal.
2. Secciones en español: hero + tesis, cómo funciona (3 pasos), agentes, tres
   superficies (UI / CLI / agentes), planes, FAQ honesto, CTA final.
3. Misma marca (estanque `pond-water-hero`, `koi-sheet`, `koi-mark`, Fraunces /
   Instrument Sans / IBM Plex Mono, tokens actuales). Sin fuentes ni colores nuevos.
4. Enlaces `/login` y `/register` siguen funcionando. Pagos se presentan como
   simulados. Sin promesas de retención 7 días, storage quotas, rate limiting ni
   audit log completo. Tiempo de provision: «en segundos», nunca «30 segundos».

## Entradas ya decididas (no se cambian)

- Solo `apps/web/src/features/landing/**` (+ ticket). Sin API, auth, billing ni otras rutas.
- Rama: `w1-landing-mobile` desde `main` @ `0fa9e91`.
- Planes siguen viniendo de `GET /plans` vía `usePlansQuery` + `formatPrice`.
- Prerender CA8 (`renderLandingHtml`) sigue montando `LandingPage`.
- Draft PR; no merge ni deploy.

## Criterios de aceptación

1. Hero muestra el copy de qué-es y el enlace «Crear cuenta» apunta a `/register`
   (prueba Vitest en `landing-page.test.tsx`).
2. Landing usable a 375 / 390 / 768 / 1440 sin scroll horizontal (evidencia:
   capturas en el PR).
3. `pnpm lint`, `pnpm test`, `pnpm build` verdes en `apps/web` (o `make check-web`).
4. FAQ / copy no afirman retención 7 días, storage, rate limiting ni audit log.
5. Ticket en `en-revision` con URL de PR al abrir el draft.

## No tocar

`apps/api/**`, auth, billing, otras rutas de `apps/web`, `packages/contracts/**`,
migraciones, `Makefile`, harness, rebase / force-push.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

Landing previa en `apps/web/src/features/landing/`. Piel: `docs/visual-guidelines.md`.
Demo Nov 11.

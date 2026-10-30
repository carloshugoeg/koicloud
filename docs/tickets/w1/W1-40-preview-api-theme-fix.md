---
id: W1-40
workstream: W1
persona: Carlos
estado: hecho
rama: w1-preview-api-theme-fix
epica: E4-04
sprint: S4
pr: "https://github.com/carloshugoeg/koicloud/pull/149"
depends_on:
---

# [W1-40] Preview API rewrite + theme CSS on Vercel

**HIGH lane** preview-infra (touches `vercel.json`, `core/config.py`, `core/db.py`, `src/api/client.ts`). Waits Carlos’s 16:00 window. Unblocks gate proof for #138 (confirm dialog) without merging #142. **Never merge** until Carlos says yes.

## Qué se ve

On Vercel **preview** deployments of `koicloud-web`:

1. `POST /api/v1/auth/login` hits the **real** preview FastAPI entry (`apps/web/api/index.py` → `apps/api` app) — not the SPA `app.html` fallback — no more 405.
2. **Theme ownership (plano option B):** this PR (**#149 / W1**) is the **single owner** of the theme token block in `apps/web/src/index.css`: `@theme inline` KoiCloud `--color-*` tokens (turquoise, marigold, bone-raised, warn, …) **plus** `.shadow-print` / `.shadow-dialog` / `.shadow-focus`. **Done-when:** plan buttons render **filled** on preview (e.g. Elegir plan = `bg-turquoise-700`).
3. Non-preview (`VERCEL_ENV≠preview`, including production) fail-closed: 404 JSON with generic `not_found` (not `pond_not_found`). Bodies over 1 MB → **413**.
4. CTA one-line wrap (`whitespace-nowrap` on Elegir plan) lives on **#137** tip `907c76c` — not duplicated here.

## Entradas ya decididas (no se cambian)

- `alembic/env.py` is **not** modified (dropped after Carlos scope check).
- `KOI_DB_SCHEMA` search_path in `core/db.py` applies **only** when `VERCEL_ENV=preview`.
- Ticket id is **W1-40** (W1-39 belongs to #148 account E1-05). Early commit message said W1-39 by mistake — do not rewrite history; this ticket is W1-40.
- Preview hosting: `apps/web/api/index.py` + `prepare-preview-api.mjs` + `vercel.json` rewrites `/api/v1/*` and `/mcp` ahead of the SPA catch-all.
- Theme token block owned by **#149 / W1** (not #137). #137 keeps plan card component styles (including CTA wrap).
- No `KOI_PREVIEW_MOCK` — real preview API only when `VERCEL_ENV=preview`.
- No OpenAPI / command signature / migration table changes.
- Do not edit #137 or #138 branches.

## Criterios de aceptación

1. Preview `POST /api/v1/auth/login` returns API JSON (200 or catalog 4xx), never SPA 405.
2. Tip `apps/web/src/index.css` ships the self-contained `@theme` + 3 shadow classes; built preview CSS emits `bg-turquoise-*` / `bg-marigold` / `bg-bone-raised` / `text-warn`.
3. Plan buttons are **filled** on Vercel preview (done-when).
4. `api/index.py` returns 404 JSON (`not_found`) when not preview; body > 1 MB → 413.
5. `make check-web` and `make check-api` pass.
6. Ticket + INDEX row; PR marked **HIGH lane**; never merge until Carlos says yes.
7. Proof screenshots of `/app/plans` at 375/768/1440 with filled buttons.

## No tocar

`packages/contracts/**`, OpenAPI, `schema.d.ts`, command signatures, `#137` / `#138` / `#142` branches, production env enabling the preview API, secrets in PR body.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.

## Referencia

#142 preview entry pattern; #137 plan card / CTA wrap (`907c76c`); gate confirm for #138.

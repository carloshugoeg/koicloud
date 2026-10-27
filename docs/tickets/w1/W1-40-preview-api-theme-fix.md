---
id: W1-40
workstream: W1
persona: Carlos
estado: en-revision
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
2. Theme token utilities (`@theme inline`, `.shadow-*`) come from **#137** — this ticket does **not** ship a duplicate theme hunk.
3. Non-preview (`VERCEL_ENV≠preview`, including production) fail-closed: 404 JSON with generic `not_found` (not `pond_not_found`). Bodies over 1 MB → **413**.

## Entradas ya decididas (no se cambian)

- `alembic/env.py` is **not** modified (dropped after Carlos scope check).
- `KOI_DB_SCHEMA` search_path in `core/db.py` applies **only** when `VERCEL_ENV=preview`.
- Ticket id is **W1-40** (W1-39 belongs to #148 account E1-05). Early commit message said W1-39 by mistake — do not rewrite history; this ticket is W1-40.
- Preview hosting: `apps/web/api/index.py` + `prepare-preview-api.mjs` + `vercel.json` rewrites `/api/v1/*` and `/mcp` ahead of the SPA catch-all.
- Theme ownership: **#137** (`w2-a2-web-gaps`). This PR drops its copy of `@theme` / `@layer base` / `.shadow-*` so the second merge does not conflict.
- No `KOI_PREVIEW_MOCK` — real preview API only when `VERCEL_ENV=preview`.
- No OpenAPI / command signature / migration table changes.
- Do not edit #137 or #138 branches.

## Criterios de aceptación

1. Preview `POST /api/v1/auth/login` returns API JSON (200 or catalog 4xx), never SPA 405.
2. Theme utilities land via #137; this PR has **no** duplicate `@theme` block.
3. `api/index.py` returns 404 JSON (`not_found`) when not preview; body > 1 MB → 413.
4. `make check-web` and `make check-api` pass.
5. Ticket + INDEX row; PR marked **HIGH lane**; never merge until Carlos says yes.
6. Proof screenshots + axe committed under `media/preview-infra/` and embedded in the PR body.

## No tocar

`packages/contracts/**`, OpenAPI, `schema.d.ts`, command signatures, `#137` / `#138` / `#142` branches, production env enabling the preview API, secrets in PR body.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.

## Referencia

#142 (`w1-e2e-preview-verify`) preview entry pattern; #137 `@theme inline` (theme owner); gate fail on #138 confirm preview.

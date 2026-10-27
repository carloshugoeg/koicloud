---
id: W1-39
workstream: W1
persona: Carlos
estado: en-curso
rama: w1-preview-api-theme-fix
epica: E4-04
sprint: S4
pr:
depends_on:
---

# [W1-39] Preview API rewrite + theme CSS on Vercel

Low-lane preview-infra. Unblocks gate proof for #138 (confirm dialog) without merging #142.

## Qué se ve

On Vercel **preview** deployments of `koicloud-web`:

1. `POST /api/v1/auth/login` hits the preview FastAPI mock (not the SPA `app.html` fallback) — no more 405.
2. Built CSS includes token utilities (`bg-marigold`, `bg-turquoise-700`, `bg-bone-raised`, `.shadow-dialog`) so theme colors paint.
3. Production (`VERCEL_ENV=production`) keeps the mock API disabled (404 JSON).

## Entradas ya decididas (no se cambian)

- Preview hosting pattern from #142: `apps/web/api/index.py` + `prepare-preview-api.mjs` + `vercel.json` rewrites `/api/v1/*` and `/mcp` ahead of the SPA catch-all that excludes `api/`.
- Theme fix from #137 approach: `@theme inline` in `index.css` (Tailwind 4 ignores `tailwind.config.ts` colors). Explicit `.shadow-*` classes.
- `KOI_PREVIEW_MOCK` / `KOI_DB_SCHEMA` only for preview; never against production data.
- No OpenAPI / command signature / migration table changes.
- Do not edit #138's branch (`w2-confirm-dialog`).

## Criterios de aceptación

1. Preview `POST /api/v1/auth/login` returns API JSON (200 or catalog 4xx), never SPA 405.
2. Preview CSS bundle contains `bg-marigold`, `bg-turquoise-700`, `bg-bone-raised`, and `.shadow-dialog`.
3. `api/index.py` returns 404 JSON when `VERCEL_ENV=production`.
4. `make check-web` and `make check-api` pass.
5. Ticket + INDEX row; PR marked low-lane preview-infra; never merge until gate re-proof asks.

## No tocar

`packages/contracts/**`, OpenAPI, `schema.d.ts`, command signatures, `#138` / `#142` branches, production env enabling the mock, secrets in PR body.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.

## Referencia

#142 (`w1-e2e-preview-verify`) preview mock; #137 `@theme inline`; gate fail on #138 confirm preview.

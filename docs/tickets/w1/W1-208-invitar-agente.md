---
id: W1-208
workstream: W1
persona: Carlos
estado: en-curso
rama: w1-208-invitar-agente
epica: "E9-02"
sprint: S7
pr:

depends_on:
  - W1-203
  - W1-204
---

# [W1-208] S7 demo: diálogo Invitar agente en el detalle de la pond (link temporal, contraseña, QR, revocar)

## Qué se ve

En el detalle del pond, el presentador abre **Invitar agente**, genera un link
temporal + contraseña (S2), ve la contraseña una sola vez, un QR del invite/link,
instrucciones de pegado para Claude Code / Cursor CLI / Codex CLI (S3), y puede
revocar para que la auth MCP falle después.

## Entradas ya decididas (no se cambian)

- Endpoints existentes: `POST/GET /api/v1/ponds/{pond_id}/temp-access` y
  `POST .../temp-access/{token_id}/revoke` (PR #211). Create → `PondTempAccessSecretOut`
  (incluye `password`); list → `PondTempAccessOut` (sin password).
- Snippets de consola: forma de `app/mcp/console_snippets.py` +
  `docs/runbooks/demo-console-mcp.md` (PR #219). No inventar contratos HTTP nuevos.
- Stack sobre `w1-204-console-mcp-snippets` (PR #219). No retarget a `main` hasta
  que #211 y #219 mergeen. No copiar PR #198. No basar en #218.

## Criterios de aceptación

1. Desde el detalle del pond, **Invitar agente** genera link temporal + contraseña.
2. La contraseña se muestra una sola vez al crear; vistas posteriores no re-muestran plaintext.
3. Se muestra un QR que codifica el invite/link.
4. Instrucciones de pegado cubren los agentes de consola de S3.
5. Revocar desde el diálogo invalida el token (MCP auth falla después).
6. Sin soporte ChatGPT/claude.ai web.

## No tocar

`packages/contracts/**`, OpenAPI, firmas de `commands/*`, migraciones, CCR nuevo,
PR #198, rama `w1-205-temp-sql-autoconfirm` (#218), ChatGPT/claude.ai web.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.

## Referencia

Issue #208 · PR #211 (S2) · PR #219 (S3) · statechart
`docs/architecture/statecharts/invitar-agente/`.

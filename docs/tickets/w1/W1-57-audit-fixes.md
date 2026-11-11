---
id: W1-57
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-audit-fixes
epica: E6-02
sprint: S8
pr: https://github.com/carloshugoeg/koicloud/pull/252
depends_on:
---

# [W1-57] Audit fixes pre-demo: nombre, scrub de password, MCP 4xx

## Qué se ve

1. Crear un pond con nombre inválido (mayúsculas, `_`, símbolos, largo fuera de
   3–40) responde **422** en REST. MCP `create_pond` con el mismo nombre falla
   como params inválidos (no 500).
2. Un segundo usuario que intenta el mismo nombre que un pond vivo recibe
   **409** `pond_name_taken` antes de encolar provision. El índice
   `ponds_user_name_uk` sigue de backstop para races del mismo dueño.
3. Tras `complete` succeeded/failed, `jobs.payload.db_password_plain` queda
   `null` o `[redacted]`. Claim sigue entregando la contraseña en claro. Retry
   reconstruye el secreto desde el pond cifrado.
4. MCP JSON-RPC con nombre de argumento desconocido o tipo malo responde
   **4xx** con error JSON-RPC `-32602`, no 500. Streamable no responde 500.

## Entradas ya decididas (no se cambian)

- Regla de nombre = la de la Web (`apps/web/src/features/ponds/pond-name.ts`):
  `^[a-z0-9-]{3,40}$`.
- Código de conflicto: `pond_name_taken` (ya en el catálogo).
- Sin CCR de OpenAPI / sin códigos nuevos / sin migración de filas viejas.
- Sin tocar billing, rate limiting, auth/temp-link scopes.

## Criterios de aceptación

1. `test_duplicate_pond_name_across_users_returns_409`
2. `test_invalid_pond_name_returns_422`
3. `test_job_payload_password_scrubbed_after_complete` (provision sigue
   succeeded; payload sin plaintext)
4. `test_mcp_bad_argument_returns_4xx_not_500_jsonrpc`
5. `test_mcp_bad_argument_returns_4xx_or_rpc_invalid_params_streamable`
6. `npm run pregate` verde. Commit `test:` primero (rojo en main), luego el fix.

## No tocar

Billing, rate limiting, auth/temp-link scopes, migraciones de datos existentes,
`packages/contracts/**`, firmas de `commands/*`, rebase / force-push.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

Pruebas en `apps/api/tests/test_audit_fixes_w1_57.py`. Antecedente de scrub de
errores: W1-200. Demo Nov 11.

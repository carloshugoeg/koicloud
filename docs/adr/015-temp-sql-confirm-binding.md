# Acceso temporal: confirmación SQL ligada al credential

## Status

Proposed (CCR TEMP-CONFIRM on issue #96, comment 6717822360). Pending authorized merge.

## Context

El acceso temporal de pond (#203 / PR #211) autentica con Basic `pond-<slug>:<password>` y permite `run_sql` en lectura. Las escrituras MCP exigen `propose → confirm`, pero `confirm_action` no está en el allowlist temporal y `confirm_action(token)` reconstruye un `AuthContext` de dueño sin pin ni scopes. Añadir solo el allowlist escalaría privilegios.

No hay sesión MCP durable por dispositivo: ambos transportes son stateless. Varios credentials temporales pueden compartir el mismo `user_id` de dueño.

## Decision

1. La sesión lógica temporal es `PondToken.id`, retenida en `AuthContext.pond_token_id` (interno). Quienes comparten el mismo link/password son el mismo principal; no hay aislamiento por dispositivo.
2. Se deriva `confirm_action` solo si el credential vivo ya concede `run_sql`. Sin lifecycle, cancel, account ni GRANT nuevos.
3. Las propuestas temporales de `run_sql_write` guardan `pond_token_id`, `pond_id` y `request_digest` (SHA-256 del envelope canónico v1). Filas legacy de dueño quedan null-bound.
4. Confirmación atómica: lock `PondToken` luego `PendingConfirmation`; un solo `UPDATE … WHERE consumed_at IS NULL`; claim durable antes del SQL; grant tipado interno (nunca un `confirm_token` truthy arbitrario); dispatch con el actor restringido.
5. Revalidación de credential/scopes/owner/pond en issue, claim y admisión final. Owner suspendido o inválido → `401 agent_bad_credentials`. MCP global off / tool o scope faltante → `403 agent_disabled`.
6. TTL = `min(now + min(confirm_ttl_seconds, 300), PondToken.expires_at)`.

## Consequences

El cliente de audiencia confirma con el mismo Basic, sin JWT de dueño. Dueño y temp no cruzan propuestas. Un token consumido no se rearma tras fallo o crash. Revoke antes de admisión niega la ejecución; SQL ya admitido puede terminar dentro del timeout de 10 s.

## Rejected alternatives

Allowlist-only; bypass de confirmación global; exigir JWT de dueño; GRANT/superuser; identidad solo por `user_id`; header MCP de sesión como identidad; locks en memoria; reintento automático de DDL; store externo de pago.

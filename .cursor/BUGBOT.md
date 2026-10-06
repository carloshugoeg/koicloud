# Bugbot — reglas de revisión para KoiCloud

Instrucciones para el revisor automático (y cualquier agente que revise PRs). Prioriza riesgos reales de este monorepo; no marques estilo salvo que viole `AGENTS.md` §8 o la piel de `docs/visual-guidelines.md`.

---

## Siempre (cualquier PR)

1. **Preview / demo:** nunca reportes un preview como listo sin comprobar **HTTP 200** en la URL y que la UI renderiza (no pantalla en blanco, no error de build). Si no puedes probar, dilo explícitamente.
2. **Secretos:** rechaza API keys, JWT secrets, `POND_PASSWORD_KEY`, tokens de node-agent, contraseñas reales o `.env` commiteado. Variables van en `.env.example` como placeholders.
3. **Migraciones:** todo cambio en `apps/api/alembic/versions/` debe ser **reversible** (`downgrade` coherente). CI ejecuta `upgrade head → downgrade base → upgrade head`; si falta `downgrade`, bloquea.
4. **Archivos generados:** `packages/contracts/openapi.json` y `apps/web/src/api/schema.d.ts` solo cambian vía `make contracts` (W1). Diff manual = rechazo.
5. **Propiedad:** ramas `w2-`/`w3-`/`w4-` no deben tocar rutas de otro workstream (job `ownership` en CI).
6. **Commits:** sin `Co-authored-by: Cursor`, Antigravity, Gemini ni trailers de herramienta.

---

## Riesgos altos por área

### Autenticación y sesión (`modules/auth`, `core/auth.py`, `core/security.py`)

- Refresh tokens y cookies: flags `HttpOnly`, `Secure` en producción, rotación coherente.
- No acortar validación de contraseña ni saltar verificación de email sin ticket/CCR.
- Errores de login con códigos del catálogo (`docs/architecture/api-surface.md` §7), no mensajes crudos.

### Pagos y facturación (`modules/billing`)

- Billing es **simulado** en alcance académico; no integrar pasarelas reales sin CCR.
- Cambios en planes, IVA o estados de suscripción deben alinearse con `data-model.md` y migraciones.

### Ponds, jobs y node-agent

- Toda mutación de pond pasa por `app/commands/*`, no por routers.
- `delete_pond` debe respetar confirmación en CLI/MCP y pre-delete backup según contrato.
- El node-agent es el **único** que llama Docker; la API solo encola jobs.

### `propose → confirm` (CLI, MCP)

- Mutaciones remotas: primera respuesta **409** con `confirmation_required`, `summary` legible y `expires_at`.
- Rechaza PRs que encadenen propose+confirm en un solo turno de agente o que omitan mostrar el `summary` al humano.
- Tokens de un solo uso; no reutilizar ni fabricar tokens en tests de producción.

### SQL y consola

- SQL del usuario solo en `commands/sql.py`, parametrizado, con `statement_timeout` y tope de filas.
- Rechaza interpolación de strings SQL en cualquier otro módulo.
- SQL write debe exigir confirmación fuera de la Web.

### Web (`apps/web`)

- Sin `dark:`, sin hex fuera de `src/index.css`, sin Inter/Roboto/Arial.
- Datos solo vía `src/api/client.ts`; sin `any`.
- Koi solo donde permite `visual-guidelines.md` §7.3 — nunca sobre tablas o datos.
- Listados con estados cargando, vacío y error.

### MCP y agent access

- Gate mínima (slug + password); documentar que no es OAuth ni producto de seguridad completo.
- Tools MCP ≤ 25 líneas; llaman a comandos, no duplican reglas.

---

## Señales de rechazo rápido

| Patrón | Veredicto |
|--------|-----------|
| `HTTPException` suelta en vez de `AppError` | REQUEST_CHANGES |
| Lógica de negocio en `router.py`, componente React o tool MCP | REQUEST_CHANGES |
| Nueva dependencia sin mención en el PR | REQUEST_CHANGES |
| `# type: ignore` / `eslint-disable` sin justificación en la misma línea | REQUEST_CHANGES |
| Editar migración ya fusionada | REQUEST_CHANGES |
| `except: pass` o errores tragados | REQUEST_CHANGES |
| Cambio de ruta OpenAPI sin CCR | REQUEST_CHANGES |
| Preview no verificado con 200 + UI | No marcar como listo |

---

## Referencias

- [`AGENTS.md`](../AGENTS.md) — fuente única para agentes
- [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) — comportamiento y flujo
- [`docs/architecture/api-surface.md`](../docs/architecture/api-surface.md) — contrato HTTP
- [`.github/CODEOWNERS`](../.github/CODEOWNERS) — rutas sensibles (`@carloshugoeg`)

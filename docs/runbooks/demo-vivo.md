# Demo en vivo — runbook operativo

Guion versionado en **`scripts/demo-vivo.sh`**. Narrativa de producto y fallbacks en
[`risks-and-demo-plan.md`](../architecture/risks-and-demo-plan.md). Deploy en VPS (solo
checklist para Carlos): [`deploy.md`](./deploy.md).

---

## Subcomandos

Desde la raíz del repo:

```bash
bash scripts/demo-vivo.sh preflight   # docker, git, puertos
bash scripts/demo-vivo.sh reset         # baja compose/ponds y libera puertos
bash scripts/demo-vivo.sh a             # Demo A — pond fijo :15432 (siempre funciona)
bash scripts/demo-vivo.sh sql           # CREATE/SELECT inventario en pond-demo
bash scripts/demo-vivo.sh b             # Demo B — seed + login + pond vía API
bash scripts/demo-vivo.sh full          # Entrega final — register → Micro → pond (API)
bash scripts/demo-vivo.sh entrega       # reset → full (ensayo completo local)
bash scripts/demo-vivo.sh all           # reset → A → B (rehearsal rápido)
```

| Subcomando | Cuándo usarlo |
|---|---|
| `preflight` | Antes de entrar al aula o abrir la exposición |
| `a` / `sql` | Plan B si el control plane falla — Postgres real sin API |
| `b` | Smoke test con usuario sembrado (`demo@koicloud.dev`) |
| `full` | Camino feliz de Entrega final por API (registro real) |
| `entrega` | Ensayo E1/E2/E3 local desde cero |

Variables útiles:

| Variable | Default | Notas |
|---|---|---|
| `SKIP_GIT=1` | — | No hace pull de `main` |
| `FORCE=1` | — | Mata PIDs que bloquean puertos (último recurso) |
| `KOI_DB_HOST_PORT` | `5432` | Remapeo si Postgres del host ocupa 5432 |
| `FULL_DEMO_EMAIL` | `presenter-…@koicloud.dev` | Cuenta nueva en `full` |
| `FULL_DEMO_POND` | `inventario-demo` | Nombre del pond en `full` |
| `DEMO_CONFIRM_DELETE=1` | `0` | Si `1`, confirma el delete al final de `full` |

---

## Qué está automatizado vs qué es manual

| Paso del guion (12 min) | Automatizado en `full` | Manual (Web / MCP / CLI) |
|---|---|---|
| Registro + verificación de correo | Sí — token desde logs del `api` | Web: pantalla de registro y verify |
| Contratar Micro | Llama `POST /subscriptions` | Web: checkout simulado. **Respuesta fixture** hasta W3-07 |
| Crear pond + poll `running` | Sí | Web: formulario «Crear pond» |
| `psql` / CREATE TABLE | Sí si hay `psql` y URI | Terminal del presentador |
| Consola SQL Web | No | Web: `SELECT * FROM items` |
| CLI `pond list` / delete / confirm | Parcial — `koicloud pond list` sí; `confirm` es W4-05 | CLI o `curl` con `X-KOI-Surface: cli` |
| MCP (Claude/Cursor) | No | Ver § MCP abajo y `risks-and-demo-plan.md` §4 |
| Admin / factura PDF | No | Tickets W3-08…W3-10 |

**Honestidad:** en dev, `auto_micro_subscription=true` asigna Micro al crear el primer pond
aunque `subscribe` no persista todavía. El script igual llama `subscribe` para ensayar el
contrato HTTP. No decir «factura persistida» hasta que W3-07 aterrice.

---

## Entrega final — guion de 12 minutos

Duración objetivo: **12 min de demo + 3 min de preguntas**. Ensayar **tres veces** (calendario
en `risks-and-demo-plan.md` §7).

### Pre-demo (5 min antes)

**Local (Mac / VM):**

```bash
bash scripts/demo-vivo.sh preflight
bash scripts/demo-vivo.sh entrega    # o full si ya hiciste reset
```

**VPS (cuando Carlos cablee el host — no inventar deploy):**

1. `curl -fsS "https://${KOICLOUD_DOMAIN}/api/v1/health"` → 200
2. En el host: `docker ps` — `api`, `worker`, `db`, `caddy` arriba; node-agent con
   `systemctl status koicloud-agent`
3. Tener abierto Claude Desktop con MCP configurado (slug + password del usuario demo)
4. Terminal con `koicloud` logueado y otra con `psql` listo
5. Video de respaldo en `~/demo-koicloud-backup.mp4`
6. Terminal local con `AGENT_MODE=mock docker compose up` como plan C

Checklist completo de secretos y layout del host: [`deploy.md`](./deploy.md).

### Minuto a minuto

| Min | Acción | Dónde |
|---|---|---|
| 0:00 | Intro: «KoiCloud — DBaaS académico. Tres superficies, una API» | Slide |
| 1:00 | Registro `demo@equipokoicloud.dev` o login | Web |
| 2:00 | Contratar Micro (pago simulado) | Web |
| 3:00 | Crear pond `inventario-demo` | Web |
| 4:00 | Copiar URI → `psql` → `CREATE TABLE items` | Terminal |
| 5:00 | Consola SQL: `SELECT * FROM items` | Web |
| 6:00 | `koicloud pond list` → `koicloud pond delete …` | CLI — propose |
| 7:00 | `koicloud confirm <token>` (o `curl` si W4-05 pendiente) | CLI |
| 7:30 | Recrear pond desde CLI | CLI |
| 8:00 | Claude: «dame un pond llamado inventario-natural» | MCP |
| 8:30 | «Confírmalo» → `confirm_action` | MCP |
| 9:30 | `SELECT now()` vía MCP | MCP |
| 10:30 | Delete con backup previo → confirm | MCP |
| 11:00 | Cierre: mismo backend, tres canales, doble confirmación | Slide |

**Frases prohibidas:** «auto-curación garantizada», «OAuth 2.1», «producción-ready», «SLA»,
«sandbox público». Usar: «demostración académica», «gate mínima para el aula», «V2 fuera de
alcance».

### MCP y fallback LLM

- Configuración: panel «Acceso agente» en Web (slug + password).
- Si el LLM no responde en 15 s: `scripts/demo-mcp-replay.py --simulate-chat` (W4-09).
- Detalle del fallback: `risks-and-demo-plan.md` §4.

### Plan B — sin control plane

```bash
bash scripts/demo-vivo.sh a
bash scripts/demo-vivo.sh sql
```

Muestra Postgres real en `:15432` mientras se arregla la API.

---

## Los tres ensayos (ritual de equipo)

| Ensayo | Cuándo | Objetivo |
|---|---|---|
| E1 | 7 días antes | Ensayo completo; medir tiempos; anotar defectos |
| E2 | 3 días antes | Ensayo con video de respaldo; fallback MCP |
| E3 | 1 día antes | Red del aula (o simulada); grabar video final |

Cada ensayo con defectos en la ruta crítica → ticket `w1/demo-fix-<n>-<slug>`. Ningún
defecto abierto el día de la exposición.

Comandos sugeridos por ensayo:

```bash
# E1 — local Docker
bash scripts/demo-vivo.sh entrega

# E2 — mismo + fallback MCP (cuando exista W4-09)
python scripts/demo-mcp-replay.py --simulate-chat

# E3 — contra VPS (Carlos)
export API_BASE="https://${KOICLOUD_DOMAIN}/api/v1"
bash scripts/demo-vivo.sh full   # sin reset si el host es compartido
```

---

## Quirks Mac / cloud VM

Ver [`agent-onboarding.md`](../agent-onboarding.md) §9 y [`local-pond.md`](./local-pond.md).

- **bash 3.2** en macOS: el script es compatible; no uses `wait -n`.
- **5432 ocupado:** `demo-vivo.sh` remapea con `KOI_DB_HOST_PORT`.
- **Bridge Docker roto en VM:** overlay `docker-compose.vm-hostnet.yml` (auto).
- **Demo A + B a la vez:** nombres distintos (`inventario-demo` vs `pond-api-demo`).

---

## Referencias

- `scripts/demo-vivo.sh`
- `docs/architecture/risks-and-demo-plan.md`
- `docs/architecture/feature-breakdown.md` (E9-06, camino MVP §3)
- `docs/runbooks/deploy.md` (VPS — solo Carlos)
- `docs/runbooks/local-pond.md`

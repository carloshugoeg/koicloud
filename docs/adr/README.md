# Architecture Decision Records

Registro de las decisiones A-01…A-12 del pack
([`../architecture/system-architecture.md`](../architecture/system-architecture.md) §8).

| ADR | Decisión |
|-----|----------|
| [001](001-modular-fastapi-monolith.md) | Monolito modular FastAPI |
| [002](002-postgres-skip-locked-queue.md) | Cola en PostgreSQL con SKIP LOCKED |
| [003](003-docker-on-vps-not-k8s.md) | Docker directo en un VPS |
| [004](004-node-agent-systemd.md) | Node-agent como proceso systemd |
| [005](005-pending-confirmations.md) | Cola `pending_confirmations` |
| [006](006-fastmcp-in-process.md) | FastMCP en el mismo proceso API |
| [007](007-agent-url-password-auth.md) | Auth de agente URL + password |
| [008](008-thin-surfaces.md) | Superficies delgadas sin dominio |
| [009](009-ephemeral-sql-console.md) | Consola SQL con conexión efímera |
| [010](010-docker-restart-no-reconciler.md) | `docker --restart=no` + reconciler |
| [011](011-local-disk-backups.md) | Backups en disco local |
| [012](012-monorepo.md) | Monorepo `koicloud` |

Estado por defecto: **Accepted**. Un cambio que contradiga un ADR abre uno nuevo; no se reescribe la historia.

# Decisiones de arquitectura

Estos registros aceptan A-01 a A-12. El resumen está en la sección 8 de `docs/architecture/system-architecture.md`. Un cambio que contradiga un registro se escribe como un ADR nuevo.

| Registro | Decisión |
| --- | --- |
| [001](001-modular-fastapi-monolith.md) | Monolito modular en FastAPI |
| [002](002-postgres-skip-locked-queue.md) | Cola de jobs en PostgreSQL |
| [003](003-docker-on-vps-not-k8s.md) | Docker en un VPS |
| [004](004-node-agent-systemd.md) | Node-agent como proceso aparte |
| [005](005-pending-confirmations.md) | Cola de confirmaciones |
| [006](006-fastmcp-in-process.md) | FastMCP en el proceso de la API |
| [007](007-agent-url-password-auth.md) | Acceso de agente con slug y contraseña |
| [008](008-thin-surfaces.md) | Superficies sin reglas de dominio |
| [009](009-ephemeral-sql-console.md) | Conexión SQL efímera por consulta |
| [010](010-docker-restart-no-reconciler.md) | Reinicio de contenedores a cargo del reconciler |
| [011](011-local-disk-backups.md) | Respaldos en disco local |
| [012](012-monorepo.md) | Un solo repositorio |

# Fuentes Mermaid del pack de arquitectura

Este directorio contiene las fuentes editables (`.mmd`) de los diagramas embebidos en los documentos del pack. Los documentos principales renderizan los diagramas en línea (GitHub renderiza Mermaid nativamente); estos archivos existen para regenerar SVG/PNG cuando haga falta o para editar sin buscar el snippet dentro del Markdown.

## Índice

| Archivo | Aparece en |
|---------|-----------|
| `01-componentes.mmd` | `system-architecture.md` §2 |
| `02-despliegue.mmd` | `system-architecture.md` §5 |
| `03-trust-boundaries.mmd` | `system-architecture.md` §6 |
| `04-ciclo-desired-observed.mmd` | `system-architecture.md` §7 |
| `05-flujo-crear-pond-web.mmd` | `interconnections.md` §2 |
| `06-flujo-cli-confirm.mmd` | `interconnections.md` §3 |
| `07-flujo-mcp-confirm.mmd` | `interconnections.md` §4 |
| `08-cola-jobs.mmd` | `interconnections.md` §5 |
| `09-reconciler-heartbeat.mmd` | `interconnections.md` §6 |
| `10-sql-console.mmd` | `interconnections.md` §7 |
| `11-backup-restore.mmd` | `interconnections.md` §8 |
| `12-metering.mmd` | `interconnections.md` §9 |
| `13-suspend-user.mmd` | `interconnections.md` §10 |
| `14-deploy.mmd` | `interconnections.md` §11 |
| `15-dependencias-epicas.mmd` | `feature-breakdown.md` §2 |
| `16-er.mmd` | `data-model.md` §1 |
| `17-pond-state-machine.mmd` | `data-model.md` §4.1 |
| `18-job-state-machine.mmd` | `data-model.md` §4.2 |
| `19-subscription-state-machine.mmd` | `data-model.md` §4.3 |

## Cómo regenerar SVG

```bash
cd docs/architecture/diagrams
npx -y @mermaid-js/mermaid-cli@11 -i 05-flujo-crear-pond-web.mmd -o 05-flujo-crear-pond-web.svg
# repetir por archivo; -e png para PNG
```

## Regla

Los diagramas embebidos en Markdown y los `.mmd` de este directorio se mantienen **sincronizados a mano**. Si editas uno, edita el otro en el mismo PR. Un job de CI podría verificarlo (futuro), pero por ahora la disciplina es humana.

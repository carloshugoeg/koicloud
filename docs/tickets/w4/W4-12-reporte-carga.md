---
id: W4-12
workstream: W4
persona: Diego
estado: abierto
rama: w4-reporte-carga
epica: "E10-04, E10-05"
sprint: S5
pr:
---

# [W4-12] Reporte de carga y tres runbooks

## Qué se ve

Entrega documental con resultados reales de k6 y tres runbooks operativos. Lo visible es evidencia fechada, vinculable desde el manual técnico y sin inventar procedimientos nuevos de despliegue.

## Entradas ya decididas (no se cambian)

- Rutas propias: `docs/reporte-carga.md` y `docs/runbooks/*.md`.
- El reporte usa salida real de k6, con fecha, commit y percentiles.
- Los tres runbooks (rutas finales): `docs/runbooks/free-disk.md`,
  `docs/runbooks/restart-agent.md`, `docs/runbooks/rollback-migration.md`.
  `docs/runbooks/local-pond.md` ya existe y no cuenta en la terna.
- `deploy.yml` sigue fuera de alcance sin aprobación de W1.

## Criterios de aceptación

1. El reporte incluye números crudos, thresholds y contexto de ejecución.
2. Quedan exactamente los tres runbooks de *Entradas*.
3. El manual técnico enlaza al reporte y a los runbooks finales.
4. Ningún runbook reescribe el pipeline de deploy ni contratos del backend.

## No tocar

- `apps/api/**`.
- `apps/cli/**`.
- `apps/node-agent/**`.
- `.github/workflows/deploy.yml` sin aprobación expresa de W1.

## Si algo falta

Respondé `BLOQUEADO` solo si hace falta un cuarto runbook o tocar `deploy.yml`.
Las tres rutas ya están en *Entradas*.

## Referencia

Imitá el PR #1 (`[W2-01] Pantalla de login`): misma estructura de archivos, mismo estilo de pruebas y misma forma de cerrar criterios en el PR.

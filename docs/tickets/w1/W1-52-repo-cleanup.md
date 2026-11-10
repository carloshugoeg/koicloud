---
id: W1-52
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-repo-cleanup
epica: E0-00
sprint: S4
pr: https://github.com/carloshugoeg/koicloud/pull/237
depends_on:
---

# [W1-52] Limpieza de repo antes de la demo del 11 nov

## Qué se ve

`docs/README.md` apunta a los cuatro documentos del curso. El texto
«Scaffold base para W2» ya no aparece en el manual de usuario. ADR 014 y el
runbook de deploy describen Hostinger KVM 1 + `KOICLOUD_DOMAIN` (sslip.io), no
Oracle Always Free como host de producción. Docs pre-repo viven en
`docs/archive/`. No hay carpetas `media/gate-*` / `media/admin-suspend-gate`
sin referencias. Las ramas remotas con PR cerrado y tip ya en `main` no
quedan colgadas. Sin cambios de comportamiento de API ni de UI.

## Entradas ya decididas (no se cambian)

- Rama: `w1-repo-cleanup`. Base: `main`.
- Ticket id: `W1-52` (W1-49 tomado por #235/#236; 50/51 reservados).
- No tocar archivos de #235, #236 ni superficies auth/email en vuelo.
- No editar `packages/contracts/**`, firmas de `app/commands/*`, ni migraciones.
- Borrar ramas remotas solo si el PR está merged/closed, no hay PR abierto, y el
  tip está contenido en `main` (ahead=0).
- `estado: en-revision` al abrir el PR draft.

## Criterios de aceptación

1. Existe `docs/README.md` con los 4 docs del curso (manual técnico, manual de
   usuario, architecture/ADRs, solid-review) y rutas exactas.
2. `docs/manual-usuario.md` no contiene «Scaffold base para W2».
3. ADR 014 y `docs/runbooks/deploy.md` nombran Hostinger KVM 1 y
   `KOICLOUD_DOMAIN`/sslip.io; `bash infra/scripts/check-oracle-deploy-ready.sh`
   sale 0.
4. Docs movidos a `docs/archive/` conservan stubs o enlaces actualizados; `rg`
   no deja rutas rotas a los nombres viejos sin redirigir.
5. `media/admin-suspend-gate` y `media/gate-*` sin referencias quedan fuera del
   árbol.
6. Tabla de ramas remotas (excepto `main`) en el PR: borradas vs conservadas con
   motivo.
7. `make check-web` y el check de deploy readiness pasan; sin cambio de API.

## No tocar

- Archivos de #235 (`w1-account-page`) y #236 (`w1-temp-link-scope`), en
  particular `docs/ARCHITECTURE.md`, `docs/architecture/api-surface.md`,
  `docs/tickets/w1/00-INDEX.md`, auth/account/temp-link.
- `packages/contracts/**`, `apps/api/alembic/**`, firmas de `app/commands/*`.
- Ramas con PR abierto, sin PR, o con commits no contenidos en `main`.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

Limpieza documental y de ramas; patrón de ticket W1 con PR draft y plantilla
`.github/PULL_REQUEST_TEMPLATE.md`.

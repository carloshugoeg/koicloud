---
id: W1-190
workstream: W1
persona: Carlos
estado: en-revision
rama: w1-190-restore-replace
epica: E6-02
sprint: S5
pr: https://github.com/carloshugoeg/koicloud/pull/195
depends_on:
---

# [W1-190] Restaurar reemplaza las filas del pond

## Qué se ve

Un respaldo de una tabla con 7 filas, restaurado 3 veces, deja esas 7 filas.
Si el dump falla después de que la carga empezó, el pond conserva las filas
anteriores y el job `restore_pond` termina `failed`.

## Entradas ya decididas (no se cambian)

- El job sigue siendo `restore_pond` en `DockerDriver.restore`. No hay job nuevo.
- El dump sigue siendo `pg_dump` plano (`--no-owner --no-acl`). No se cambia a `-Fc`.
- El esquema de la aplicación es `public`.
- Sin códigos de error nuevos. Sin cambios en `packages/contracts/**`.
- Firmas de `app/commands/*`, tablas, columnas y enums no se tocan.

## Criterios de aceptación

1. Una tabla con 7 filas, respaldada y restaurada 3 veces, sigue con esas 7 filas.
   Prueba `test_restore_three_times_leaves_seven_rows`.
2. Un restore que falla a mitad deja las filas previas y el job termina `failed`.
   Prueba `test_restore_failure_keeps_previous_rows`.
3. `docs/gate-checklist.md` tiene la fila del conteo y una prueba plantilla.

## No tocar

- `.github/workflows/deploy.yml`.
- `packages/contracts/**` y el catálogo de `ErrorCode`.
- Firmas de `app/commands/*`. Tablas, columnas y enums.
- La prueba nueva después del commit `test:`. El arreglo no la edita.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

Issue #190 y el amendment r8 en #96. El diálogo de restaurar ya dice que
reemplaza. `docs/architecture/interconnections.md` §8 describe el drop del esquema.

---
id: W2-20
workstream: W2
persona: Jason
estado: en-revision
rama: w2-restore-job-runs
epica: "E6-02, E6-03"
sprint: S5
pr: "https://github.com/carloshugoeg/koicloud/pull/179"
depends_on: W2-08
---

# [W2-20] La restauración sale de la cola y la pantalla lo muestra

## Qué se ve

En Respaldos, al restaurar un respaldo de demo-pond, el aviso deja de quedarse en «estado queued». El job `restore_pond` corre en el node-agent con `AGENT_MODE=docker` y termina en `succeeded` o en `failed` con el motivo. La página consulta el job y muestra ese avance y el estado final.

## Entradas ya decididas (no se cambian)

- Pantalla `/app/ponds/{id}/backups`, aviso con `data-testid="restore-queued"`.
- `POST /api/v1/ponds/{id}/restore` sigue respondiendo `202` con el job en `queued`.
- El node-agent ya despacha `restore_pond` en `agent/handlers`. No se cambia la firma de `restore_backup`.
- Textos en español. El token de estado (`queued`, `running`, `succeeded`, `failed`) se muestra en mono, como hoy.
- Sin modo oscuro, sin hex nuevos, sin koi sobre la tabla.

## Criterios de aceptación

1. Con `DockerDriver`, un job `restore_pond` pasa de `queued` a `succeeded` cuando el dump existe. Prueba `test_restore_job_reaches_succeeded_on_docker_agent`.
2. Si el dump no está, el mismo camino termina en `failed` y `last_error` contiene `backup_not_found`. Prueba `test_restore_job_fails_when_backup_file_is_missing`.
3. Playwright: el aviso muestra `queued` y luego el estado final `succeeded`. Prueba `restore job status reaches succeeded`.
4. La pantalla no hace scroll horizontal a 375, 768 ni 1440.

## No tocar

- `.github/workflows/deploy.yml`.
- Firmas ya existentes de `app/commands/*`. Tablas, columnas y enums.
- La prueba nueva después del commit `test:`. El arreglo no la edita.
- Consola SQL, administración y facturación.
- El timeout de un job que sigue `queued` porque el agente no late. Queda fuera. El reconciler ya cubre un job `running` zombi.

## Si algo falta

Respondé `BLOQUEADO: requiere <CCR | ticket para Wn> porque <razón>` y pará
**solo** si hay que *editar* un contrato congelado o un archivo ajeno.
Si el comando ya existe, llamalo. Si `depends_on` no aterrizó, `ESPERA`.
No inventes endpoints, campos, tablas, códigos de error ni pantallas.

## Referencia

- `docs/statechart/level2/restore-job.md`
- `apps/web/src/features/ponds/backups-page.tsx`
- `apps/node-agent/agent/handlers/restore_pond.py`
- `docs/tickets/w2/W2-18-plan-picker-escape.md`

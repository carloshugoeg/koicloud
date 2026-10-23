# Liberar disco en el VPS

Síntoma: `create_pond` o un backup responde `disk_full` (507), o
`df -h` muestra menos del **10 %** libre en el volumen de datos.
Backups y logs viven en disco local (ADR-011). No hay almacén externo.

Rutas típicas en el host:

| Ruta | Qué ocupa |
|------|-----------|
| `/var/lib/koicloud/backups/` | dumps de ponds (`daily`, `on_demand`, `pre_delete`) |
| `/var/lib/koicloud/backups/internal/` | dump diario del Postgres de control (cron, 7 d) |
| `/var/lib/docker/` | imágenes, capas y volúmenes de ponds |
| journal / logs de Docker | ruido operativo |

## 1. Medir

```bash
df -h /
df -h /var/lib/koicloud /var/lib/docker 2>/dev/null || true
sudo du -sh /var/lib/koicloud/backups/* 2>/dev/null | sort -h
docker system df
```

## 2. Purgar backups de ponds (retención 30 d en `daily`)

Los `daily` se pueden borrar a mano si tienen más de 30 días.
`pre_delete` no tiene retención automática: compactá solo con criterio
(pond ya borrado y sin necesidad de auditoría).

```bash
# Dailies viejos (ejemplo: más de 30 días)
find /var/lib/koicloud/backups -type f -name '*.dump' -mtime +30 -print
# Revisá la lista, luego:
# find /var/lib/koicloud/backups -type f -name '*.dump' -mtime +30 -delete
```

El dump interno ya se limpia solo (`infra/scripts/backup-internal-db.sh`,
`find … -mtime +7 -delete`). Si hace falta espacio ya:

```bash
ls -lt /var/lib/koicloud/backups/internal/
# borrá dumps internos viejos a mano si el cron no corrió
```

## 3. Docker sin tocar ponds en uso

```bash
docker container prune -f
docker image prune -f
# Solo si sabés que no hay volúmenes huérfanos útiles:
# docker volume prune -f
docker system df
```

No borres contenedores `koicloud-*` / `koi-pond-*` en `running`.
Para reiniciar el agent tras un prune agresivo:
[`restart-agent.md`](./restart-agent.md).

## 4. Comprobar

```bash
df -h /
curl -fsS "https://${KOICLOUD_DOMAIN}/api/v1/health"
```

Si sigue bajo el 10 % libre, no sigas creando ponds hasta liberar más o
ampliar el disco del VPS. Este runbook no cambia el pipeline de deploy.

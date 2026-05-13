# Runbook: Offsite Backup

## Objetivo

El backup local del VPS no cubre perdida completa de la maquina o del proveedor.
Este runbook define el backup offsite diario de PostgreSQL mediante `rclone`,
con verificacion de tamano remoto y retencion minima de 30 dias.

## Contrato

- El dump se genera desde Docker Compose con `pg_dump --format=custom`.
- El destino remoto se configura fuera del repo en `rclone`.
- Los secretos no se guardan en git.
- El script falla si no puede verificar el tamano remoto.
- El ultimo backup correcto escribe timestamp en `/var/lib/esdata/last_offsite_backup`.

## Configuracion del VPS

Instalar y configurar `rclone` con un proveedor distinto al del VPS, por ejemplo
Backblaze B2, S3 o Hetzner Storage Box:

```bash
sudo apt-get update
sudo apt-get install -y rclone jq
sudo -u deploy rclone config
```

Crear `/etc/esdata/offsite-backup.env` con permisos estrictos:

```bash
sudo install -o deploy -g deploy -m 0600 /dev/null /etc/esdata/offsite-backup.env
sudoedit /etc/esdata/offsite-backup.env
```

Contenido esperado:

```bash
export ESDATA_BACKUP_REMOTE='b2-esdata:esdata-backups'
export ESDATA_BACKUP_RETENTION_DAYS='30'
export ESDATA_BACKUP_ENV_FILE='/etc/esdata/esdata.env'
export ESDATA_BACKUP_COMPOSE_FILE='/srv/esdata/infra/deploy/docker-compose.prod.yml'
```

El nombre `b2-esdata:esdata-backups` es un ejemplo. Debe apuntar al remoto real
configurado en `rclone`.

## Verificacion manual

```bash
cd /srv/esdata
. /etc/esdata/offsite-backup.env
bash scripts/backup-offsite.sh --check-config
bash scripts/backup-offsite.sh
cat /var/lib/esdata/last_offsite_backup
```

## Cron

Instalar la entrada versionada:

```bash
sudo cp /srv/esdata/infra/deploy/cron/esdata-offsite-backup /etc/cron.d/esdata-offsite-backup
sudo chmod 0644 /etc/cron.d/esdata-offsite-backup
sudo systemctl reload cron || sudo systemctl reload crond
```

La ejecucion diaria queda a las 02:00 Europe/Madrid.

## Restore Drill Offsite

Descargar el ultimo backup desde el remoto:

```bash
mkdir -p /tmp/esdata-offsite-restore
rclone copy 'b2-esdata:esdata-backups' /tmp/esdata-offsite-restore --max-age 2d --include 'esdata_*.dump.gz'
ls -lh /tmp/esdata-offsite-restore
```

Restaurar en base temporal, nunca en produccion:

```bash
COMPOSE='docker compose --env-file /etc/esdata/esdata.env -f /srv/esdata/infra/deploy/docker-compose.prod.yml'
$COMPOSE exec postgres psql -U "$POSTGRES_USER" -d postgres -c 'DROP DATABASE IF EXISTS esdata_offsite_test WITH (FORCE);'
$COMPOSE exec postgres psql -U "$POSTGRES_USER" -d postgres -c 'CREATE DATABASE esdata_offsite_test;'
gunzip -c /tmp/esdata-offsite-restore/esdata_YYYYMMDD_HHMMSS.dump.gz \
  | $COMPOSE exec -T postgres pg_restore -U "$POSTGRES_USER" -d esdata_offsite_test
$COMPOSE exec postgres psql -U "$POSTGRES_USER" -d esdata_offsite_test -c "
SELECT 'aeat_modelo' AS tabla, COUNT(*) FROM aeat_modelo
UNION ALL SELECT 'norma', COUNT(*) FROM norma
UNION ALL SELECT 'articulo', COUNT(*) FROM articulo
UNION ALL SELECT 'query_audit_log', COUNT(*) FROM query_audit_log;
"
$COMPOSE exec postgres psql -U "$POSTGRES_USER" -d postgres -c 'DROP DATABASE esdata_offsite_test WITH (FORCE);'
```

## Criterio De Aceptacion

- `scripts/backup-offsite.sh --check-config` pasa en VPS.
- `scripts/backup-offsite.sh` sube un fichero remoto con tamano verificado.
- El restore drill en `esdata_offsite_test` devuelve filas para tablas criticas.
- `/var/lib/esdata/last_offsite_backup` tiene menos de 26 horas.

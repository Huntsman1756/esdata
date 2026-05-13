# Runbook: Backup y Restore de PostgreSQL

## Objetivo

Procedimientos para backup y restore de la base de datos PostgreSQL de esdata.

## Contexto

- Base de datos: PostgreSQL 16 (pgvector)
- Imagen: `pgvector/pgvector:pg16`
- Volumen Docker: `esdata-postgres`
- Usuario por defecto: `esdata`
- DB por defecto: `esdata`

---

## Backup completo (pg_dumpall)

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml exec postgres pg_dumpall -U esdata > infra/backups/esdata-full-$(date +%Y%m%d-%H%M%S).sql
```

### Backup de esquema + datos (pg_dump)

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml exec postgres pg_dump -U esdata -d esdata --format=custom --file=/tmp/esdata-backup.dump
```

### Backup solo de esquema

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml exec postgres pg_dump -U esdata -d esdata --schema-only > infra/backups/esdata-schema-$(date +%Y%m%d-%H%M%S).sql
```

### Backup de un solo schema/tabla

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml exec postgres pg_dump -U esdata -d esdata --table=norma > infra/backups/esdata-norma-$(date +%Y%m%d-%H%M%S).sql
```

### Backup con compresión

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml exec postgres pg_dump -U esdata -d esdata --format=custom | gzip > infra/backups/esdata-backup-$(date +%Y%m%d-%H%M%S).dump.gz
```

## Restaurar desde backup

### Restaurar backup completo (pg_dumpall)

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml exec -T postgres psql -U esdata -d postgres < infra/backups/esdata-full-YYYYMMDD-HHMMSS.sql
```

### Restaurar backup custom (pg_dump)

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml exec -T postgres pg_restore -U esdata -d esdata --clean --if-exists /tmp/esdata-backup.dump
```

### Restaurar backup comprimido

```bash
gunzip -c infra/backups/esdata-backup-YYYYMMDD-HHMMSS.dump.gz | docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml exec -T postgres pg_restore -U esdata -d esdata --clean --if-exists
```

### Restaurar solo esquema

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml exec -T postgres psql -U esdata -d esdata < infra/backups/esdata-schema-YYYYMMDD-HHMMSS.sql
```

## Backup automático con cron

### Contenedor de backup (Docker Compose, recomendado)

El contenedor `backup` se incluye en el perfil `prod` de
`infra/deploy/docker-compose.prod.yml`. Escribe backups diarios
comprimidos en `infra/deploy/backups/` con retención de 7 días.

```bash
# Iniciar con el perfil prod (incluye backup)
docker compose --env-file /etc/esdata/esdata.env \
  -f infra/deploy/docker-compose.prod.yml up -d

# Verificar que el contenedor de backup está corriendo
docker compose --env-file /etc/esdata/esdata.env \
  -f infra/deploy/docker-compose.prod.yml logs backup

# Listar backups generados
ls -lh infra/deploy/backups/

# Ver logs del último backup
docker compose --env-file /etc/esdata/esdata.env \
  -f infra/deploy/docker-compose.prod.yml logs backup | tail -20
```

> **Nota:** El volumen `infra/deploy/backups/` está en `.gitignore`.
> Nunca hacer commit de los archivos de backup.

### En el host (Linux)

```bash
# Backup diario a las 3am, retención 30 días
0 3 * * * mkdir -p /srv/backups/esdata && ENV_FILE=/etc/esdata/esdata.env BACKUP_DIR=/srv/backups/esdata /srv/esdata/scripts/ops/backup-postgres.sh
0 3 * * * find /srv/backups/esdata -name "*.gz" -mtime +7 -delete
```

### Backup offsite

El backup local no es suficiente para produccion: si se pierde la maquina o el
proveedor, se pierde tambien el backup. El backup offsite diario se gestiona con
`scripts/backup-offsite.sh` y un remoto `rclone` configurado fuera del repo.

Ver [offsite-backup.md](./offsite-backup.md).

### En Windows (Task Scheduler / PowerShell)

```powershell
# backup-esdata.ps1
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = "G:\_Proyectos\esdata\infra\backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

docker compose --env-file G:\_Proyectos\esdata-secrets\esdata.env `
  -f G:\_Proyectos\esdata\infra\deploy\docker-compose.prod.yml `
  exec -T postgres pg_dump -U esdata -d esdata --format=custom |
  Out-File -FilePath "$backupDir\esdata-$timestamp.dump"

# Limpieza: borrar backups de mas de 30 dias
Get-ChildItem $backupDir -Filter "esdata-*.dump" |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
  Remove-Item -Force
```

## Verificar integridad del backup

```bash
# Verificar que el archivo no esta corrompido (custom format)
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml exec postgres pg_restore -l infra/backups/esdata-backup.dump

# Verificar SQL (formato texto)
head -50 infra/backups/esdata-full-YYYYMMDD-HHMMSS.sql
grep -c "CREATE TABLE" infra/backups/esdata-full-YYYYMMDD-HHMMSS.sql

# Contar tablas en el backup
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml exec postgres pg_restore -l infra/backups/esdata-backup.dump | grep "TABLE DATA" | wc -l
```

## Tamaño de la base de datos

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c "SELECT pg_size_pretty(pg_database_size('esdata'));"
```

## Checklist de restore

1. [ ] Verificar integridad del archivo de backup
2. [ ] Notificar downtime si es restore en produccion
3. [ ] Detener API y workers: `docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml stop api web worker-boe worker-dgt worker-teac worker-modelos worker-bdns worker-borme worker-cnmv worker-sepblac worker-cendoj worker-eurlex worker-bde worker-aepd`
4. [ ] Ejecutar restore
5. [ ] Verificar integridad post-restore (contar filas de tablas criticas)
6. [ ] Reiniciar API y workers
7. [ ] Validar `/health` y `/status`
8. [ ] Ejecutar smoke tests: `pytest apps/api/tests/test_smoke.py -v`
9. [ ] Notificar restore completado

## Tablas principales para verificar post-restore

```sql
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;
```

```sql
SELECT 'norma' as tbl, count(*) FROM norma
UNION ALL SELECT 'articulo', count(*) FROM articulo
UNION ALL SELECT 'version_articulo', count(*) FROM version_articulo
UNION ALL SELECT 'documento_interpretativo', count(*) FROM documento_interpretativo
UNION ALL SELECT 'aeat_modelo', count(*) FROM aeat_modelo
UNION ALL SELECT 'sync_log', count(*) FROM sync_log;
```

## Notas

- Los backups custom format (`pg_restore`) son preferibles por compresion y flexibilidad.
- Para restores grandes, usar `--jobs=N` en `pg_restore` para paralelismo.
- El volumen `esdata-postgres` es el unico que contiene datos persistentes. Los otros son efimeros.
- Nunca hacer backup cuando hay un worker de BOE/DGT escribiendo si la consistencia es critica: pausar workers primero.

# Operaciones — Runbooks

## Resumen

Este documento cubre la operación diaria de esdata en producción.
Todos los comandos asumen que se ejecutan desde la raiz del repo en el servidor.

## Workflow del agente

- Secuencia operativa estandar: `agent-workflow.md`
- Memoria operativa acumulada para futuros agentes: `agent-notes.md`
- Matriz de verificacion por area y cierre de sesion: `verification-matrix.md`
- Estado activo y siguiente paso: `../master-execution-roadmap.md`
- Reglas globales: `../../AGENTS.md`

## Monitoreo de salud

### Ver estado de todos los servicios

```bash
docker compose -f infra/deploy/docker-compose.prod.yml ps
```

Todos deben mostrar `healthy` o `up`.

### Ver logs en tiempo real

```bash
# Todos los servicios
docker compose -f infra/deploy/docker-compose.prod.yml logs -f

# Servicio específico
docker compose -f infra/deploy/docker-compose.prod.yml logs -f api
docker compose -f infra/deploy/docker-compose.prod.yml logs -f worker-boe
```

### Ver consumo de recursos

```bash
docker stats --no-stream
```

### Healthcheck manual

```bash
# API
curl -s https://api.tudominio.com/health

# Web
curl -s -o /dev/null -w "%{http_code}" https://tudominio.com
```

## Operaciones de base de datos

### Ver version de migraciones

```bash
docker compose -f infra/deploy/docker-compose.prod.yml exec api alembic current
```

### Aplicar migraciones pendientes

```bash
docker compose -f infra/deploy/docker-compose.prod.yml exec api alembic upgrade head
```

### Revertir una migracion

```bash
# Revertir la ultima
docker compose -f infra/deploy/docker-compose.prod.yml exec api alembic downgrade -1

# Revertir a una version especifica
docker compose -f infra/deploy/docker-compose.prod.yml exec api alembic downgrade <revision_id>
```

### Ver historial de migraciones

```bash
docker compose -f infra/deploy/docker-compose.prod.yml exec api alembic history
docker compose -f infra/deploy/docker-compose.prod.yml exec api alembic log --rev-range base:head
```

### Backup de base de datos

```bash
# Backup completo
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres pg_dump -U esdata esdata > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup con gzip
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres pg_dump -U esdata esdata | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Backup con cron (ya configurado en server-installation.md)
```

### Restaurar base de datos

```bash
# Restaurar desde archivo SQL
gunzip -c backup_20260425_030000.sql.gz | docker compose -f infra/deploy/docker-compose.prod.yml exec -T postgres psql -U esdata esdata

# Restaurar desde archivo sin gzip
cat backup_20260425_030000.sql | docker compose -f infra/deploy/docker-compose.prod.yml exec -T postgres psql -U esdata esdata
```

### Verificacion de integridad

```bash
# Contar documentos por tabla
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "SELECT 'version_articulo' AS tabla, COUNT(*) FROM version_articulo
   UNION ALL SELECT 'norma', COUNT(*) FROM norma
   UNION ALL SELECT 'documento', COUNT(*) FROM documento
   UNION ALL SELECT 'modelo_aeat', COUNT(*) FROM modelo_aeat;"

# Verificar extensiones
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "SELECT extname FROM pg_extension WHERE extname IN ('pg_trgm', 'vector');"

# Verificar tamanio de DB
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "SELECT pg_size_pretty(pg_database_size('esdata'));"
```

### Limpieza de indices corruptos

```bash
# Detectar indices corruptos
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "SELECT indexrelid::regclass AS indice, indrelid::regclass AS tabla
   FROM pg_index i
   JOIN pg_class c ON c.oid = i.indexrelid
   WHERE NOT c.relhasindex;"

# Reconstruir indice
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "REINDEX INDEX indice_corrupto;"
```

## Operaciones de workers

### Ejecutar worker una vez

```bash
docker compose -f infra/deploy/docker-compose.prod.yml run --rm worker-boe python boe.py --run-once
docker compose -f infra/deploy/docker-compose.prod.yml run --rm worker-dgt python dgt.py --run-once
docker compose -f infra/deploy/docker-compose.prod.yml run --rm worker-modelos python modelos.py --run-once
```

### Ver logs de un worker

```bash
docker compose -f infra/deploy/docker-compose.prod.yml logs worker-boe
```

### Reiniciar un worker

```bash
docker compose -f infra/deploy/docker-compose.prod.yml restart worker-boe
```

### Detener todos los workers

```bash
docker compose -f infra/deploy/docker-compose.prod.yml stop worker-*
```

### Reiniciar todos los workers

```bash
docker compose -f infra/deploy/docker-compose.prod.yml restart worker-*
```

## Operaciones de API

### Reiniciar API

```bash
docker compose -f infra/deploy/docker-compose.prod.yml restart api
```

### Ver logs de errores

```bash
docker compose -f infra/deploy/docker-compose.prod.yml logs api | grep ERROR
```

### Verificar dependencias

```bash
# Verificar que la API puede conectar a Postgres
docker compose -f infra/deploy/docker-compose.prod.yml exec api python -c \
  "from db import SessionLocal; SessionLocal().execute('SELECT 1'); print('OK')"
```

## Operaciones de Web

### Reiniciar Web

```bash
docker compose -f infra/deploy/docker-compose.prod.yml restart web
```

### Verificar build

```bash
docker compose -f infra/deploy/docker-compose.prod.yml logs web | grep -i error
```

## Operaciones de Caddy (SSL)

### Verificar certificados

```bash
docker compose -f infra/deploy/docker-compose.prod.yml exec caddy caddy list-certificates
```

### Forzar renovacion de certificados

```bash
docker compose -f infra/deploy/docker-compose.prod.yml exec caddy caddy reload --config /etc/caddy/Caddyfile
```

### Ver logs de Caddy

```bash
docker compose -f infra/deploy/docker-compose.prod.yml logs caddy
```

## Operaciones de mantenimiento

### Limpiar imagenes no usadas

```bash
docker image prune -f
```

### Limpiar volumes no usados

```bash
docker volume prune -f
```

### Limpiar logs de contenedores

```bash
# Truncar logs de un contenedor
docker compose -f infra/deploy/docker-compose.prod.yml logs --tail=0 api > /dev/null

# O reiniciar contenedor (reinicia logs automaticamente)
docker compose -f infra/deploy/docker-compose.prod.yml restart api
```

### Actualizar sistema operativo

```bash
# Actualizar paquetes del SO
sudo apt update && sudo apt upgrade -y

# Reiniciar si es necesario
sudo reboot

# Despues del reboot, verificar servicios
docker compose -f infra/deploy/docker-compose.prod.yml ps
```

## Escalado de emergencia

### Escenario: API consume demasiada memoria

```bash
# 1. Reiniciar API
docker compose -f infra/deploy/docker-compose.prod.yml restart api

# 2. Si persiste, escalar memoria del worker
#    (modificar docker-compose.prod.yml y hacer restart)
```

### Escenario: Postgres consume todo el disco

```bash
# 1. Verificar tamanio de tablas
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS size
   FROM pg_tables ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC LIMIT 10;"

# 2. Limpiar tablas temporales si existen
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "DELETE FROM tabla_temporal WHERE fecha < NOW() - INTERVAL '30 days';"

# 3. Vacuum
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "VACUUM ANALYZE;"
```

### Escenario: Workers no ingieren datos

```bash
# 1. Verificar logs
docker compose -f infra/deploy/docker-compose.prod.yml logs worker-boe | tail -50

# 2. Verificar migraciones
docker compose -f infra/deploy/docker-compose.prod.yml exec api alembic current

# 3. Aplicar migraciones si es necesario
docker compose -f infra/deploy/docker-compose.prod.yml exec api alembic upgrade head

# 4. Ejecutar worker manualmente
docker compose -f infra/deploy/docker-compose.prod.yml run --rm worker-boe python boe.py --run-once
```

## Incidentes

### API responde 502 Bad Gateway

```bash
# 1. Verificar que API esta corriendo
docker compose -f infra/deploy/docker-compose.prod.yml ps api

# 2. Verificar logs
docker compose -f infra/deploy/docker-compose.prod.yml logs api | tail -50

# 3. Verificar healthcheck
docker compose -f infra/deploy/docker-compose.prod.yml inspect api --format='{{.State.Health.Status}}'

# 4. Reiniciar
docker compose -f infra/deploy/docker-compose.prod.yml restart api
```

### Web no carga

```bash
# 1. Verificar que Web esta corriendo
docker compose -f infra/deploy/docker-compose.prod.yml ps web

# 2. Verificar logs
docker compose -f infra/deploy/docker-compose.prod.yml logs web | tail -50

# 3. Verificar que API es accesible desde web
docker compose -f infra/deploy/docker-compose.prod.yml exec web curl -s http://api:8000/health
```

### Postgres no acepta conexiones

```bash
# 1. Verificar que Postgres esta corriendo
docker compose -f infra/deploy/docker-compose.prod.yml ps postgres

# 2. Verificar logs
docker compose -f infra/deploy/docker-compose.prod.yml logs postgres | tail -50

# 3. Reiniciar
docker compose -f infra/deploy/docker-compose.prod.yml restart postgres

# 4. Si persiste, verificar disco
df -h
```

### SSL no funciona

```bash
# 1. Verificar Caddy
docker compose -f infra/deploy/docker-compose.prod.yml ps caddy

# 2. Verificar logs
docker compose -f infra/deploy/docker-compose.prod.yml logs caddy | tail -50

# 3. Verificar DNS
dig api.tudominio.com
dig tudominio.com

# 4. Verificar puertos abiertos
sudo ss -tlnp | grep -E ':(80|443)'
```

## Checklist semanal de mantenimiento

- [ ] Verificar que todos los servicios estan `healthy`
- [ ] Revisar logs de errores en los ultimos 7 dias
- [ ] Verificar espacio en disco (`df -h`)
- [ ] Verificar que backups se estan generando (`ls /backups/`)
- [ ] Verificar que workers estan ingiriendo datos
- [ ] Verificar que certificados SSL no expiran
- [ ] Verificar consumo de memoria y CPU

## Checklist mensual de mantenimiento

- [ ] Actualizar Docker Engine y Compose
- [ ] Actualizar imagenes base de contenedores
- [ ] Revisar y limpiar logs antiguos
- [ ] Verificar integridad de backups (restaurar en staging)
- [ ] Revisar tamanio de base de datos y optimizar si necesario
- [ ] Revisar politicas de retention de backups

## Referencias

- `docs/deployment/overview.md` — overview de despliegue
- `docs/deployment/server-installation.md` — instalacion en servidor
- `docs/deployment/rollback.md` — procedimientos de rollback
- `docs/database.md` — estrategia de migraciones
- `infra/deploy/docker-compose.prod.yml` — configuracion de despliegue

# [REFERENCE] Handoff de infraestructura

> Documento de referencia de infraestructura. La fuente activa unica de estado y ejecucion es `docs/master-execution-roadmap.md`.

## Resumen

esdata se despliega con Docker Compose. No se usa Railway (DEPRECATED). La infraestructura de referencia es `infra/deploy/docker-compose.prod.yml`.

## Arquitectura de despliegue

```
┌─────────────────────────────────────────────────────────┐
│                    Servidor Ubuntu                      │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ esdata   │  │ esdata   │  │ esdata   │  │ esdata │ │
│  │ api      │  │ web      │  │ worker-  │  │ db     │ │
│  │ :8000    │  │ :3000    │  │ boe      │  │ :5432  │ │
│  │          │  │          │  │          │  │ pg     │ │
│  │          │  │          │  │          │  │ :6379  │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
│         │              │              │                │
│         └──────────────┴──────────────┘                │
│                    PostgreSQL 16                        │
│                    pgvector extension                   │
└─────────────────────────────────────────────────────────┘
```

## Servicios Docker Compose

### api (FastAPI)

- **Imagen**: `esdata-api:latest` (construida desde `apps/api/Dockerfile`)
- **Puerto**: 8000 (mapeado como 8001 en local)
- **Red**: `esdata-net`
- **Depende de**: `db`
- **Reiniciar**: `unless-stopped`
- **Healthcheck**: GET `/v1/status`
- **Variables clave**: `DATABASE_URL`, `BOE_API_BASE`, `ESDATA_API_BASE_URL`

### web (Next.js)

- **Imagen**: `esdata-web:latest` (construida desde `apps/web/Dockerfile`)
- **Puerto**: 3000 (mapeado como 3005 en local)
- **Red**: `esdata-net`
- **Depende de**: `api`
- **Reiniciar**: `unless-stopped`
- **Variables clave**: `ESDATA_API_BASE_URL` (apunta a `api:8000`)

### db (PostgreSQL)

- **Imagen**: `pgvector/pgvector:pg16`
- **Puerto**: 5432 (mapeado como 5434 en local)
- **Red**: `esdata-net`
- **Reiniciar**: `always`
- **Persistencia**: Volume `esdata-pgdata` en `/var/lib/postgresql/data`
- **Init scripts**: `infra/sql/` montado en `/docker-entrypoint-initdb.d/`
- **Variables**: `POSTGRES_USER=esdata`, `POSTGRES_PASSWORD`, `POSTGRES_DB=esdata`

### redis

- **Imagen**: `redis:7-alpine`
- **Puerto**: 6379 (mapeado como 6379 en local)
- **Red**: `esdata-net`
- **Reiniciar**: `unless-stopped`
- **Persistencia**: Volume `esdata-redis-data`

### Workers

- **Imagen**: `esdata-workers:latest` (construida desde `apps/workers/Dockerfile`)
- **Servicios**: `worker-boe`, `worker-modelos`, `worker-bdns`, `worker-borme`, etc.
- **Red**: `esdata-net`
- **Depende de**: `db`
- **Reiniciar**: `unless-stopped`
- **Variables clave**: `DATABASE_URL`, `BOE_API_BASE`, `SYNC_INTERVAL_SECONDS`

## Volumen de datos

| Volume | Montaje | Contenido | Persistencia |
|--------|---------|-----------|--------------|
| `esdata-pgdata` | `/var/lib/postgresql/data` | Base de datos PostgreSQL | Si |
| `esdata-redis-data` | `/data` | Datos de Redis | Si |

## Despliegue de produccion

### Pre-requisitos del servidor

- Ubuntu 22.04+
- Docker >= 24.0
- Docker Compose >= 2.20
- Puertos disponibles: 80, 443, 8001, 3005, 5434, 6379
- Memoria minima: 2GB RAM
- Disco minimo: 10GB

### Pasos de despliegue

1. Clonar repositorio en el servidor
2. Copiar `.env` con las variables de produccion
3. Ejecutar `infra/deploy/server-setup.sh` para configurar el servidor
4. Ejecutar `infra/deploy/deploy.sh` para construir y lanzar los contenedores

### Comandos operativos

```bash
# Levantar servicios
docker compose -f infra/deploy/docker-compose.prod.yml up -d

# Ver logs
docker compose -f infra/deploy/docker-compose.prod.yml logs -f api
docker compose -f infra/deploy/docker-compose.prod.yml logs -f worker-boe

# Reiniciar un servicio
docker compose -f infra/deploy/docker-compose.prod.yml restart api

# Parar todos los servicios
docker compose -f infra/deploy/docker-compose.prod.yml down

# Parar y borrar datos (DESTRUCTIVO)
docker compose -f infra/deploy/docker-compose.prod.yml down -v

# Verificar healthcheck
docker compose -f infra/deploy/docker-compose.prod.yml ps

# Backup de base de datos
docker exec esdata-db pg_dump -U esdata esdata > backup.sql

# Restore de base de datos
docker exec -i esdata-db psql -U esdata esdata < backup.sql
```

## Migraciones de base de datos

### SQL init scripts

Los archivos en `infra/sql/` se ejecutan automaticamente en orden numerico al primer inicio de la base de datos:

1. `000_docker_init.sql` — Init especifico para Docker
2. `002_fulltext_search.sql` — Configuracion fulltext
3. `003_modelos_aeat.sql` — Tablas modelos AEAT
4. `004_modelos_v2.sql` — Schema modelos v2
5. `004_norma_classification.sql` — Clasificacion de normas
6. `005_indexes.sql` — Indices criticos de rendimiento
7. `006_pgvector.sql` — Extension pgvector + embeddings

### Migraciones Alembic

Para migraciones posteriores al deploy inicial:

```bash
# Crear nueva migracion
alembic revision -m "descripcion"

# Aplicar migraciones pendientes
alembic upgrade head

# Revertir ultima migracion
alembic downgrade -1

# Ver historial de migraciones
alembic history --verbose
```

Configuracion en `alembic.ini`.

## Monitoring

### Healthcheck

El endpoint `/v1/status` devuelve el estado de la API y la base de datos.

### Logs

Los logs de cada servicio se gestionan con `docker compose logs`. Configurar `LOG_LEVEL` en `.env` para ajustar el nivel de detalle.

### Metricas

No se configuran metricas externas en el deploy base. Se puede integrar con Prometheus + Grafana montando un sidecar o exportador de metricas de PostgreSQL.

## Seguridad

- Sin autenticacion en endpoints publicos
- Base de datos con autenticacion por usuario/password
- Docker: usuario `app` non-root en API
- Sin secretos en capas de imagen
- Imagen base fijada (no `latest`)
- Redis sin autenticacion (solo accesible desde `esdata-net`)

## Backup

### Base de datos

```bash
# Backup completo
docker exec esdata-db pg_dump -U esdata esdata > backup_$(date +%Y%m%d).sql

# Backup comprimido
docker exec esdata-db pg_dump -U esdata esdata | gzip > backup_$(date +%Y%m%d).sql.gz

# Restaurar
docker exec -i esdata-db psql -U esdata esdata < backup_20260425.sql
```

### Volmenes

```bash
# Backup de volumes
docker run --rm -v esdata-pgdata:/data -v $(pwd):/backup alpine tar czf /backup/pgdata_backup.tar.gz -C /data .
```

## Troubleshooting

### API no responde

```bash
# Ver logs
docker compose -f infra/deploy/docker-compose.prod.yml logs api

# Verificar healthcheck
docker compose -f infra/deploy/docker-compose.prod.yml ps

# Reiniciar
docker compose -f infra/deploy/docker-compose.prod.yml restart api
```

### Base de datos lenta

```bash
# Ver conexiones activas
docker exec esdata-db psql -U esdata -c "SELECT count(*) FROM pg_stat_activity;"

# Ver queries lentas
docker exec esdata-db psql -U esdata -c "SELECT query, now() - query_start as duration FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC LIMIT 10;"

# Verificar indexes
docker exec esdata-db psql -U esdata -c "\di" esdata
```

### Workers no procesan

```bash
# Ver logs del worker
docker compose -f infra/deploy/docker-compose.prod.yml logs worker-boe

# Verificar conexion a DB
docker exec esdata-worker-boe python -c "from runtime import get_database_url; print(get_database_url())"

# Reiniciar worker
docker compose -f infra/deploy/docker-compose.prod.yml restart worker-boe
```

## Referencias

- `infra/deploy/docker-compose.prod.yml` — Despliegue de produccion
- `infra/deploy/server-setup.sh` — Script de setup del servidor
- `infra/deploy/deploy.sh` — Script de despliegue
- `infra/sql/` — Schema y migraciones SQL
- `docker-compose.yml` — Despliegue de desarrollo local
- `apps/api/Dockerfile` — Imagen de la API
- `apps/workers/Dockerfile` — Imagen de los workers
- `apps/web/Dockerfile` — Imagen del frontend

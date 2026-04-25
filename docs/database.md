# Base de datos

## Resumen

- **Motor**: PostgreSQL 16
- **Extensiones**: `pg_trgm`, `vector` (pgvector)
- **Gestion de schema**: Alembic (migraciones programaticas)
- **SQL historico**: `infra/sql/` (referencia, no se ejecuta en despliegue)

## Arquitectura

```
PostgreSQL 16
├── pg_trgm (busqueda full-text con trigramas)
├── vector (pgvector — busqueda semantica)
├── 14 tablas principales
├── 20+ indices
└── 1 trigger + 2 funciones PL/pgSQL
```

## Tablas principales

### legislacion

| Tabla | Descripcion | Filas estimadas |
|-------|-------------|-----------------|
| `norma` | Metadatos de normas (LIVA, LIRPF, etc.) | ~20 |
| `articulo` | Articulos de cada norma | ~3000 |
| `version_articulo` | Versiones historicas del texto | ~15000 |
| `documento_seccion` | Secciones de documentos | ~5000 |
| `documento_fragmento` | Fragmentos con embedding | ~50000 |

### doctrina

| Tabla | Descripcion | Filas estimadas |
|-------|-------------|-----------------|
| `documento_interpretativo` | Consultas DGT, resoluciones TEAC, BORME, BDNS | ~500 |
| `documento_articulo` | Enlaces documento<->articulo | ~2000 |

### compliance

| Tabla | Descripcion | Filas estimadas |
|-------|-------------|-----------------|
| `obligacion_regulatoria` | Obligaciones fiscales | ~50 |
| `obligacion_documento` | Enlaces obligacion<->documento | ~200 |
| `empresa` | Empresas referenciadas | ~100 |
| `documento_empresa` | Enlaces documento<->empresa | ~300 |

### modelos_aeat

| Tabla | Descripcion | Filas estimadas |
|-------|-------------|-----------------|
| `aeat_modelo` | Modelos (216, 349, 303, etc.) | ~30 |
| `modelo_campana` | Campanas de cada modelo | ~60 |
| `modelo_casilla` | Casillas por campana | ~500 |
| `modelo_clave` | Claves de codigo por campana | ~200 |
| `modelo_instruccion` | Instrucciones por campana | ~300 |
| `modelo_normativa` | Normativa BOE por modelo | ~100 |
| `modelo_formato` | Formatos de registro | ~50 |

### operacion

| Tabla | Descripcion | Filas estimadas |
|-------|-------------|-----------------|
| `sync_log` | Registros de ingestion | ~500 |
| `materia` | Taxonomia curada | ~30 |
| `articulo_materia` | Enlaces articulo<->materia | ~200 |
| `eval_history` | Resultados de evaluacion | ~10 |
| `eval_query` | Resultados por query | ~100 |

## Estrategia de migraciones

### Alembic (ACTUAL)

Alembic es la herramienta oficial para evolucionar el schema.

```bash
# Ver revision actual
make db-current
# o
alembic current

# Aplicar todas las migraciones pendientes
make db-upgrade
# o
alembic upgrade head

# Crear nueva migracion despues de cambiar modelos SQLAlchemy
alembic revision --autogenerate -m "descripcion_corta"

# Rollback una revision
alembic downgrade -1

# Rollback a una revision especifica
alembic downgrade <revision_id>
```

#### Convencion de nombres

```
YYYYMMDD_NNNN_descripcion_corta.py
```

- `YYYYMMDD`: fecha de creacion
- `NNNN`: numero secuencial
- `descripcion_corta`: snake_case, maximo 3 palabras

#### Reglas

1. **Cada cambio de schema va en una migracion**
2. **Las migraciones son irreversibles cuando alteran datos** (baseline)
3. **Usar `IF NOT EXISTS` / `IF EXISTS`** para idempotencia
4. **No borrar migraciones viejas** — solo agregar nuevas
5. **Probar en local antes de aplicar en produccion**

#### Migraciones existentes

| Revision | Archivo | Descripcion | Reversible |
|----------|---------|-------------|------------|
| `20260416_0001` | `baseline_schema.py` | Schema inicial (18 tablas) | NO |
| `20260418_0002` | `modelo_campana_operativa.py` | Tablas modelos AEAT | Parcial |
| `20260418_0003` | `modelo_campana_operativa_provenance.py` | Provenance modelos | Parcial |
| `20260424_0004` | `doctrina_fulltext.py` | Full-text doctrina | Parcial |
| `20260424_0005` | `chunking_schema.py` | Tablas chunking | Parcial |
| `20260425_0006` | `eval_history.py` | Tablas evaluacion | Parcial |
| `20260425_0007` | `critical_indexes.py` | Indexes criticos | Parcial |
| `20260425_0008` | `obligaciones_operativas.py` | Campos operativos obligaciones | Parcial |

### SQL historico (REFERENCIA)

Los archivos en `infra/sql/` son referencias historicas. **NO se ejecutan en despliegue**.

| Archivo | Descripcion | Estado |
|---------|-------------|--------| |
| `init.sql` | Schema base + seeds minimos | Migrado a Alembic |
| `002_fulltext_search.sql` | Search vectors + triggers | Migrado a Alembic |
| `003_modelos_aeat.sql` | Tablas modelos AEAT | Migrado a Alembic |
| `004_modelos_v2.sql` | Refactorizacion modelos | Migrado a Alembic |
| `004_norma_classification.sql` | Clasificacion normas | Migrado a Alembic |
| `005_indexes.sql` | Indexes criticos | Migrado a Alembic |
| `006_pgvector.sql` | Extension vector + embeddings | **NO migrado** (nueva feature) |

Nota: `006_pgvector.sql` necesita ejecucion manual en produccion antes de los workers de embeddings.

## Bootstrap de base de datos

### Local (desarrollo)

```bash
# 1. Levantar Postgres con Docker Compose
docker compose up -d db

# 2. Aplicar schema con Alembic
make db-upgrade

# 3. Ejecutar pgvector (si se usa busqueda semantica)
psql "$(DATABASE_URL)" -f infra/sql/006_pgvector.sql

# 4. Ingerir datos con workers
make worker-boe
```

### Produccion

```bash
# 1. Levantar infra completa
docker compose -f infra/deploy/docker-compose.prod.yml up -d db

# 2. Esperar a que Postgres este listo
docker compose -f infra/deploy/docker-compose.prod.yml exec db pg_isready

# 3. Aplicar schema
docker compose -f infra/deploy/docker-compose.prod.yml exec api alembic upgrade head

# 4. Aplicar pgvector (una vez, primera vez)
docker compose -f infra/deploy/docker-compose.prod.yml exec db psql -f /docker-entrypoint-initdb.d/060_pgvector.sql

# 5. Iniciar workers
docker compose -f infra/deploy/docker-compose.prod.yml up -d workers
```

## Backup y restore

### Backup

```bash
# Backup completo (dump logico)
pg_dump "$DATABASE_URL" > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup solo schema (sin datos)
pg_dump --schema-only "$DATABASE_URL" > schema_backup.sql

# Backup con compresion
pg_dump "$DATABASE_URL" | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Backup via Docker Compose
docker compose exec db pg_dump -U esdata esdata > backup.sql
```

### Restore

```bash
# Restore desde backup completo
psql "$DATABASE_URL" < backup_20260425_120000.sql

# Restore con compresion
gunzip -c backup_20260425_120000.sql.gz | psql "$DATABASE_URL"

# Restore via Docker Compose
cat backup.sql | docker compose exec -T db psql -U esdata esdata
```

### Backup automatizado (cron)

```bash
# En crontab del servidor — backup diario a las 3am
0 3 * * * pg_dump "$DATABASE_URL" | gzip > /backups/esdata_$(date +\%Y\%m\%d_\%H\%M\%S).sql.gz
0 3 * * * find /backups -name "esdata_*.sql.gz" -mtime +30 -delete
```

## Variables de entorno relacionadas

| Variable | Uso |
|----------|-----|
| `DATABASE_URL` | URL de conexion principal |
| `DATABASE_PUBLIC_URL` | URL publica (scripts auxiliares) |
| `PGHOST` / `PGPORT` / `PGUSER` / `PGPASSWORD` / `PGDATABASE` | Alternativas a DATABASE_URL |

## Health check

```bash
# Verificar conexion
psql "$DATABASE_URL" -c "SELECT 1"

# Verificar tablas principales
psql "$DATABASE_URL" -c "\dt"

# Contar filas en tablas principales
psql "$DATABASE_URL" -c "
  SELECT 'norma' as tabla, COUNT(*) FROM norma
  UNION ALL SELECT 'articulo', COUNT(*) FROM articulo
  UNION ALL SELECT 'version_articulo', COUNT(*) FROM version_articulo
  UNION ALL SELECT 'documento_interpretativo', COUNT(*) FROM documento_interpretativo
  UNION ALL SELECT 'sync_log', COUNT(*) FROM sync_log;
"
```

## Referencias

- `alembic.ini` — configuracion Alembic
- `alembic/env.py` — logica de ejecucion de migraciones
- `alembic/versions/` — historial de migraciones
- `infra/sql/` — SQL historico de referencia
- `docker-compose.yml` — Postgres en `db` (puerto 5432)
- `infra/deploy/docker-compose.prod.yml` — Postgres en produccion

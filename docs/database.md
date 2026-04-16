# Base de datos

## Motor

- PostgreSQL

## Rol en el sistema

La base de datos es el repositorio principal de:

- legislacion normalizada y versionada
- doctrina interpretativa DGT y TEAC
- enlaces entre doctrina y articulos
- modelos AEAT, campanas, casillas, claves e instrucciones
- trazas operativas de workers en `sync_log`

## Bootstrap actual

El proyecto mantiene dos capas:

- SQL historico/manual en `infra/sql/`
- migraciones formales en Alembic para la evolucion futura

Orden actual de aplicacion:

1. `infra/sql/init.sql`
2. `infra/sql/002_fulltext_search.sql`
3. `infra/sql/003_modelos_aeat.sql`
4. `infra/sql/004_modelos_v2.sql`
5. `infra/sql/004_norma_classification.sql`

## Seeds

Scripts relevantes:

- `scripts/seed-modelos.py`
- `scripts/seed-modelos-v2.py`

## Alembic

Artefactos introducidos:

- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/20260416_0001_baseline_schema.py`

Comandos:

- `make db-upgrade`
- `make db-current`

## Estrategia recomendada

1. mantener `infra/sql/` como referencia historica y bootstrap heredado
2. usar Alembic para todos los cambios nuevos de schema
3. no aplicar cambios manuales de esquema en produccion sin reflejarlos en Alembic

## Validaciones utiles

- comprobar que `sync_log` recibe ejecuciones
- comprobar cobertura via `/v1/legislacion/cobertura`
- usar `scripts/validate-cron-run.py` para revisar enlaces doctrinales

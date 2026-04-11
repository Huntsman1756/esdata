# Postmortem Sprint 2

## Resumen

El sprint cerro con la API publica, el worker BOE, el cron diario, la cobertura por norma y la busqueda full-text funcionando en produccion sobre Railway.

## Sintomas iniciales

- `worker-boe` fallaba al arrancar en Railway.
- `cron-boe-daily` estaba mal montado desde el monorepo.
- `esdata` arrancaba pero no quedaba publica o respondia con `502`.
- La busqueda avanzada devolvia `500` en produccion.

## Causas raices

### Workers

- `DATABASE_URL` en Railway usaba `postgresql://...` y SQLAlchemy intentaba cargar `psycopg2`, pero el proyecto usa `psycopg`.
- La base de datos de produccion arrancaba vacia y el worker asumia tablas como `sync_log` ya existentes.
- El bootstrap del worker necesitaba crear `pg_trgm` antes del indice trigram.
- Los servicios de Railway para workers no estaban bien configurados inicialmente para el monorepo.

### API publica

- `apps/api/Dockerfile` fijaba `uvicorn` en el puerto `8000`.
- Railway asigna `PORT` dinamico; por eso el servicio arrancaba pero el dominio publico quedaba inestable.
- El dominio publico necesito rebinding para que el edge apuntara al despliegue correcto.

### Busqueda full-text

- El codigo de `apps/api/services/search.py` asumía que `version_articulo.search_vector` ya existia.
- En produccion no se habia aplicado `infra/sql/002_fulltext_search.sql`, asi que `/v1/legislacion/buscar` devolvia `500`.

## Cambios aplicados

### Workers

- bootstrap de esquema minimo desde `apps/workers/boe.py`
- creacion de `pg_trgm` antes del indice
- soporte robusto para BD vacia en Railway
- Dockerfile flexible para build desde `apps/workers` o desde la raiz del repo
- variables de Railway corregidas:
  - `DATABASE_URL=postgresql+psycopg://...`
  - `BOE_API_BASE=https://www.boe.es/datosabiertos/api/legislacion-consolidada`

### API

- `apps/api/Dockerfile` actualizado para usar `${PORT}`
- MCP montado en `/mcp`
- endpoints faltantes completados
- servicio de busqueda centralizado en `apps/api/services/search.py`

### Base de datos

- aplicada `infra/sql/002_fulltext_search.sql` en produccion
- columna `search_vector` creada
- indice `idx_version_articulo_search_vector` creado
- trigger `trg_version_articulo_search_vector` creado
- backfill completado: `941 / 941`

## Estado final

- `esdata`: `SUCCESS`
- `worker-boe`: `SUCCESS`
- `cron-boe-daily`: `SUCCESS`
- `Postgres`: `SUCCESS`

## Evidencias finales

- `/health` responde `200`
- `/status` responde `200`
- `/v1/legislacion` responde `200`
- `/v1/legislacion/cobertura` responde `200`
- `/v1/legislacion/buscar?q=tipo+reducido&norma=LIVA` responde `200`
- la respuesta de busqueda incluye `fragmento`, `<mark>` y `rank`
- `worker-boe` registra ejecuciones correctas en `sync_log`
- cobertura real cargada para `LGT`, `LIRPF`, `LIS` y `LIVA`

## Lecciones

- En Railway, un deploy `SUCCESS` no garantiza que el dominio publico ya haya reconciliado el cambio de instancia.
- En monorepos, los servicios con Dockerfile deben quedar blindados frente a `rootDirectory` inconsistentes.
- Si un endpoint nuevo depende de una migracion, esa migracion debe tratarse como paso obligatorio del deploy.

## Siguiente iteracion

- incorporar doctrina DGT y TEAC como corpus real
- mejorar taxonomia curada de materias
- ampliar fuentes regulatorias mas alla del nucleo fiscal

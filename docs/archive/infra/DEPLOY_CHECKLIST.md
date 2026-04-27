# [HISTORICAL] Deploy checklist — sprint 2

> **NOTA: HISTORICO — Railway DEPRECATED**
>
> Railway YA NO se usa como plataforma de despliegue. Este documento se mantiene como referencia historica.
> El despliegue de referencia es Docker Compose (`infra/deploy/docker-compose.prod.yml`).
> Ver `docs/operations/runbooks/deploy-compose.md` para el deploy actual.

## Antes del deploy (Railway — DEPRECATED)

[ ] Confirmar que el servicio Railway de la API se llama `esdata` y tiene `DATABASE_URL` (DEPRECATED)

## Bootstrap de BD (solo si el Postgres esta vacio)

[ ] Crear esquema base:
    psql $DATABASE_URL -f infra/sql/init.sql

[ ] Aplicar full-text:
    psql $DATABASE_URL -f infra/sql/002_fulltext_search.sql

[ ] Crear tablas de modelos AEAT v1:
    psql $DATABASE_URL -f infra/sql/003_modelos_aeat.sql

[ ] Crear tablas de modelos AEAT v2:
    psql $DATABASE_URL -f infra/sql/004_modelos_v2.sql

[ ] Aplicar clasificacion de `norma`:
    psql $DATABASE_URL -f infra/sql/004_norma_classification.sql

[ ] Seed inicial de modelos AEAT:
    python scripts/seed-modelos.py --db-url $DATABASE_URL
    python scripts/seed-modelos-v2.py --db-url $DATABASE_URL --campana 2025

## Migraciones incrementales (si el Postgres ya existe)

[ ] Aplicar migracion contra el Postgres real:
    psql $DATABASE_URL -f infra/sql/002_fulltext_search.sql

[ ] Aplicar migracion contra el Postgres real:
    psql $DATABASE_URL -f infra/sql/003_modelos_aeat.sql

[ ] Aplicar migracion contra el Postgres real:
    psql $DATABASE_URL -f infra/sql/004_modelos_v2.sql

[ ] Aplicar migracion contra el Postgres real:
    psql $DATABASE_URL -f infra/sql/004_norma_classification.sql

[ ] Reejecutar seeds idempotentes si faltan datos de modelos:
    python scripts/seed-modelos.py --db-url $DATABASE_URL
    python scripts/seed-modelos-v2.py --db-url $DATABASE_URL --campana 2025

[ ] Verificar que backfill completo:
    psql $DATABASE_URL -c "SELECT COUNT(*) FILTER (WHERE search_vector IS NOT NULL) AS con_vector, COUNT(*) AS total FROM version_articulo;"
    -> `con_vector` debe coincidir con `total`

[ ] Verificar que el trigger existe:
    psql $DATABASE_URL -c "SELECT tgname FROM pg_trigger WHERE tgrelid = 'version_articulo'::regclass;"

## Deploy

[ ] git add + git commit (usar COMMIT_MSG.txt)
[ ] git push → Railway despliega automáticamente
[ ] Esperar healthcheck verde en Railway dashboard para `esdata`
[ ] Esperar deploy verde de `web` via `.github/workflows/deploy-web.yml` si hubo cambios en `apps/web`
[ ] Confirmar en Railway que `worker-boe`, `worker-dgt`, `worker-teac` y `worker-modelos` tambien estan en verde
[ ] Confirmar en Railway que `cron-boe-daily`, `cron-dgt-weekly`, `cron-teac-weekly` y `cron-modelos-daily` estan creados con el comando correcto
[ ] Confirmar en Railway que el servicio `web` existe, tiene dominio publico y variable `ESDATA_API_BASE_URL`
[ ] Verificar variables operativas minimas en Railway:
    - `esdata`: `DATABASE_URL`
    - `worker-dgt`: `DATABASE_URL`, `WORKER_CMD=python dgt.py`, `DGT_SSL_VERIFY` si hace falta
    - `cron-dgt-weekly`: `DATABASE_URL`, `WORKER_CMD=python dgt.py --run-once`
    - `worker-teac`: `DATABASE_URL`, `WORKER_CMD=python teac.py`, `TEAC_SEED_URLS`
    - `cron-teac-weekly`: `DATABASE_URL`, `WORKER_CMD=python teac.py --run-once`, `TEAC_SEED_URLS`
    - `worker-modelos`: `DATABASE_URL`, `MODELOS_SYNC_INTERVAL` si se quiere ajustar el loop
    - `cron-modelos-daily`: `DATABASE_URL`
    - `web`: `ESDATA_API_BASE_URL=https://esdata-production.up.railway.app`

## Smoke tests post-deploy

[ ] curl https://esdata-production.up.railway.app/health
    → {"status":"ok"}

[ ] curl https://esdata-production.up.railway.app/openapi.json
    → OpenAPI de FastAPI accesible publicamente

[ ] curl https://web-production-ecb5.up.railway.app
    → home del buscador con cobertura y estado operativo

[ ] curl "https://web-production-ecb5.up.railway.app/buscar?q=iva&tab=legislacion"
    → resultados del frontend para legislacion

[ ] curl "https://web-production-ecb5.up.railway.app/doctrina/00/01454/2023/00/00"
    → detalle doctrina renderizado

[ ] curl "https://web-production-ecb5.up.railway.app/articulo/LIVA/104"
    → detalle de articulo renderizado

[ ] curl "https://esdata-production.up.railway.app/v1/buscar?q=tipo+reducido"
    → resultados con "fragmento" que contiene <mark>

[ ] curl "https://esdata-production.up.railway.app/v1/materias"
    → lista de materias con `articulos_count`

[ ] curl "https://esdata-production.up.railway.app/v1/legislacion/LIVA/articulos/91"
    → texto + confianza.nivel >= 1

[ ] curl "https://esdata-production.up.railway.app/v1/legislacion/ITPAJD"
    → devuelve `tipo_documento=real_decreto_legislativo` y `estado_cobertura=ingestada`

[ ] curl "https://esdata-production.up.railway.app/v1/legislacion/ITPAJD/articulos"
    → devuelve al menos un articulo de `ITPAJD`

[ ] curl "https://esdata-production.up.railway.app/v1/buscar?q=transmisiones&norma=ITPAJD"
    → devuelve al menos un resultado de legislacion para `ITPAJD`

[ ] curl "https://esdata-production.up.railway.app/v1/doctrina/buscar?q=deduccion"
    → responde (aunque sea vacío si no hay doctrina aún)

[ ] curl "https://esdata-production.up.railway.app/v1/doctrina/buscar?q=iva&organismo_emisor=DGT"
    → devuelve resultados DGT reales

[ ] curl "https://esdata-production.up.railway.app/v1/doctrina/buscar?q=iva&organismo_emisor=TEAC"
    → devuelve resultados TEAC reales

[ ] curl "https://esdata-production.up.railway.app/v1/doctrina/00/01362/2024/00/00"
    → devuelve `articulos_relacionados` con `LIVA 89` y `confianza_enlace=1.0`

[ ] curl "https://esdata-production.up.railway.app/v1/modelos"
    → devuelve lista de modelos AEAT con conteos

[ ] curl "https://esdata-production.up.railway.app/v1/modelos/100"
    → devuelve detalle de modelo con `campanas`, `casillas` e `instrucciones`

[ ] curl https://esdata-production.up.railway.app/mcp
    → responde con protocolo MCP (no 404)

[ ] railway logs --service worker-boe --tail 50
    → debe mostrar sincronizaciones o al menos arranque sin excepciones

[ ] railway logs --service worker-dgt --tail 50
    → debe mostrar sincronizaciones DGT o al menos arranque sin excepciones

[ ] railway logs --service worker-teac --tail 50
    → debe mostrar sincronizaciones TEAC o al menos arranque sin excepciones

## Si algo falla

- /v1/buscar no usa <mark>: probablemente la migración no se ejecutó
  → verificar: SELECT search_vector IS NOT NULL FROM version_articulo LIMIT 1

- /mcp devuelve 404: verificar que `mount_mcp(app)` esta en `apps/api/main.py`
  -> revisar `railway logs --service esdata --tail 100`

- `/status` o endpoints con BD devuelven 500: comparar `DATABASE_URL` de `esdata` con `worker-boe`
  -> debe usar `postgresql+psycopg://...`, no `postgresql://...`

- `/v1/modelos` devuelve 500 o vacio en Railway:
  -> comprobar que se aplicaron `003_modelos_aeat.sql` y `004_modelos_v2.sql`
  -> reejecutar `scripts/seed-modelos.py` y `scripts/seed-modelos-v2.py`

- `worker-boe` falla al crear indice trigram: verificar que `pg_trgm` existe
  -> `CREATE EXTENSION IF NOT EXISTS pg_trgm;`

- TEAC devuelve 0 documentos procesados:
  -> verificar `TEAC_SEED_URLS` en `worker-teac` y `cron-teac-weekly`
  -> comprobar que `teac.py` sigue parseando markup real de DYCTEA

- TEAC aparece sin enlaces:
  -> comprobar en detalle que la resolucion tenga `articulos_relacionados`
  -> revisar patrones en `apps/workers/boe.py::_extract_doctrina_refs`

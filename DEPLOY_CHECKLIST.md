# Deploy checklist — sprint 2

## Antes del deploy (una sola vez, en producción)

[ ] Ejecutar migracion contra el Postgres real:
    psql $DATABASE_URL -f infra/sql/002_fulltext_search.sql

[ ] Verificar que backfill completo:
    psql $DATABASE_URL -c "SELECT COUNT(*) FILTER (WHERE search_vector IS NOT NULL) AS con_vector, COUNT(*) AS total FROM version_articulo;"
    -> `con_vector` debe coincidir con `total`

[ ] Verificar que el trigger existe:
    psql $DATABASE_URL -c "SELECT tgname FROM pg_trigger WHERE tgrelid = 'version_articulo'::regclass;"

## Deploy

[ ] git add + git commit (usar COMMIT_MSG.txt)
[ ] git push → Railway despliega automáticamente
[ ] Esperar healthcheck verde en Railway dashboard para `esdata`
[ ] Confirmar en Railway que `worker-boe` y `cron-boe-daily` tambien estan en verde

## Smoke tests post-deploy

[ ] curl https://esdata-production.up.railway.app/health
    → {"status":"ok"}

[ ] curl "https://esdata-production.up.railway.app/v1/buscar?q=tipo+reducido"
    → resultados con "fragmento" que contiene <mark>

[ ] curl "https://esdata-production.up.railway.app/v1/materias"
    → lista de materias con `articulos_count`

[ ] curl "https://esdata-production.up.railway.app/v1/legislacion/LIVA/articulos/91"
    → texto + confianza.nivel >= 1

[ ] curl "https://esdata-production.up.railway.app/v1/doctrina/buscar?q=deduccion"
    → responde (aunque sea vacío si no hay doctrina aún)

[ ] curl https://esdata-production.up.railway.app/mcp
    → responde con protocolo MCP (no 404)

[ ] railway logs --service worker-boe --tail 50
    → debe mostrar sincronizaciones o al menos arranque sin excepciones

## Si algo falla

- /v1/buscar no usa <mark>: probablemente la migración no se ejecutó
  → verificar: SELECT search_vector IS NOT NULL FROM version_articulo LIMIT 1

- /mcp devuelve 404: verificar que `mount_mcp(app)` esta en `apps/api/main.py`
  -> revisar `railway logs --service esdata --tail 100`

- `/status` o endpoints con BD devuelven 500: comparar `DATABASE_URL` de `esdata` con `worker-boe`
  -> debe usar `postgresql+psycopg://...`, no `postgresql://...`

- `worker-boe` falla al crear indice trigram: verificar que `pg_trgm` existe
  -> `CREATE EXTENSION IF NOT EXISTS pg_trgm;`

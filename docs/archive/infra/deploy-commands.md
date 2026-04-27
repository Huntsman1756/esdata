# [HISTORICAL] Railway deploy commands

> **NOTA: HISTORICO — Railway DEPRECATED**
>
> Railway YA NO se usa como plataforma de despliegue. Este documento es una referencia historica obsoleta.
> El despliegue de referencia es Docker Compose (`infra/deploy/docker-compose.prod.yml`).
> Ver `docs/operations/runbooks/deploy-compose.md` para el deploy actual.
>
> NO usar estos comandos en nuevas sesiones. NO proponer Railway.

# PRE-REQUISITOS HISTORICOS (Railway)
# ============================================================
# - CLI de Railway instalada: pip install railway (DEPRECATED)
# - railway login (DEPRECATED)
# - Proyecto Railway creado: railway link <project-id> (DEPRECATED)
# - Postgres provisioning: railway add postgresql (DEPRECATED)

# ============================================================
# PASO 1: Variables de entorno (HISTORICO - Railway)
# ============================================================
# railway variables --service esdata (DEPRECATED)
# Si no tiene DATABASE_URL:
# railway variables set DATABASE_URL="..." --service esdata (DEPRECATED)

# ============================================================
# PASO 2: Ejecutar SQL migrations (HISTORICO - Railway)
# ============================================================
# Railway expone el DATABASE_URL. Usar psql local para aplicar: (DEPRECATED)
# Obtener el DATABASE_URL en formato psql-compatible (sin +psycopg) (DEPRECATED)
# export PG_URL="postgresql://user:pass@host:5432/railway" (DEPRECATED)
# ^^^^ sustituir con el valor real de Railway, cambiando postgresql+psycopg:// por postgresql:// (DEPRECATED)

psql "$PG_URL" -f infra/sql/init.sql
psql "$PG_URL" -f infra/sql/002_fulltext_search.sql
psql "$PG_URL" -f infra/sql/003_modelos_aeat.sql
psql "$PG_URL" -f infra/sql/004_modelos_v2.sql
psql "$PG_URL" -f infra/sql/004_norma_classification.sql

# Verificar que todo existe:
psql "$PG_URL" -c "\dt"
# Debe mostrar: norma, articulo, version_articulo, documento_interpretativo,
# documento_articulo, materia, articulo_materia, sync_log,
# aeat_modelo, modelo_articulo, modelo_campana, modelo_casilla,
# modelo_clave, modelo_instruccion, modelo_normativa

# Verificar extensiones:
psql "$PG_URL" -c "SELECT extname FROM pg_extension WHERE extname IN ('pg_trgm', 'unaccent');"

# Verificar que search_vector tiene datos:
psql "$PG_URL" -c "SELECT COUNT(*) FILTER (WHERE search_vector IS NOT NULL) AS con_vector, COUNT(*) AS total FROM version_articulo;"
# Nota: con_vector = 0 si la BD esta vacia (normal antes del seed)

# ============================================================
# PASO 3: Seed de modelos AEAT
# ============================================================
# Necesitas psycopg2-binary instalado localmente: pip install psycopg2-binary

python scripts/seed-modelos.py --db-url "$DATABASE_URL"
python scripts/seed-modelos-v2.py --db-url "$DATABASE_URL" --campana 2025

# Verificar seed:
psql "$PG_URL" -c "SELECT COUNT(*) FROM aeat_modelo;"
# Debe mostrar >= 20 modelos

psql "$PG_URL" -c "SELECT m.codigo, COUNT(mc.id) as casillas FROM aeat_modelo m LEFT JOIN modelo_campana mc ON mc.modelo_id = m.id GROUP BY m.codigo ORDER BY m.codigo LIMIT 10;"

# ============================================================
# PASO 4: Deploy a Railway
# ============================================================
git add -A
git commit -m "deploy: pydantic response models + gpt openapi spec + worker per-campaign scrape"
git push origin main

# Railway despliega automaticamente al recibir push.
# Si necesitas forzar un deploy manual desde la CLI, NO uses `apps/api --path-as-root`
# cuando `railway.toml` ya define `rootDirectory`, porque Railway acaba buscando
# `/apps/api` o `/apps/workers` dentro de un artefacto ya recortado y falla.
# Comando correcto:
#   railway up --service esdata --project 41c53da7-ba65-4308-9713-8c3a5e4e7706 --environment 9ffb36ae-902c-4552-9474-32f03125a3bb --detach
# Verificar en dashboard o CLI:
railway logs --service esdata --tail 30
# Debe mostrar: Uvicorn running on 0.0.0.0:XXXX

# ============================================================
# PASO 5: Smoke tests post-deploy
# ============================================================
# Obtener el URL publico de la API:
railway domain --service esdata
# Ejemplo: https://esdata-production.up.railway.app

export API_URL="https://esdata-production.up.railway.app"

# Health check:
curl -s "$API_URL/health" | python -m json.tool
# Esperado: {"status": "ok", ...}

# OpenAPI spec accesible:
curl -s "$API_URL/openapi.json" | python -c "import sys,json; d=json.load(sys.stdin); print(f'OpenAPI {d[\"openapi\"]}: {len(d[\"paths\"])} paths, {len(d[\"components\"][\"schemas\"])} schemas')"
# Esperado: OpenAPI 3.1.0: 25+ paths, 25+ schemas

# Legislacion search:
curl -s "$API_URL/v1/legislacion/buscar?q=iva" | python -c "import sys,json; d=json.load(sys.stdin); print(f'Busqueda: {len(d[\"resultados\"])} resultados')"

# Modelos list:
curl -s "$API_URL/v1/modelos" | python -c "import sys,json; d=json.load(sys.stdin); print(f'Modelos: {len(d[\"modelos\"])} modelos')"

# Modelo detail:
curl -s "$API_URL/v1/modelos/100" | python -c "import sys,json; d=json.load(sys.stdin); print(f'Modelo 100: {d[\"nombre\"]}, {d[\"campana_activa\"]}, {len(d[\"casillas\"])} casillas')"

# ============================================================
# PASO 6: Importar en ChatGPT Builder
# ============================================================
# Opcion A: URL directa (la API ya sirve /openapi.json completo)
# En el builder de ChatGPT -> Actions -> Import from URL:
#   $API_URL/openapi.json

# Opcion B: Spec reducida para GPT (solo 7 endpoints, mas limpia)
# Subir docs/openapi-gpt.json al builder

# Prompt del Custom GPT:
# Eres un asistente fiscal espanol. Usa la API esdata para:
# - buscar_legislacion: localizar articulos por texto
# - get_articulo: obtener texto de un articulo concreto
# - buscar_doctrina: consultas DGT/TEAC
# - get_doctrina: documento doctrinal completo
# - list_modelos: listado modelos AEAT
# - get_modelo: detalle completo de un modelo
# Nunca inventes contenido. Si la API no devuelve datos, dilo.

# ============================================================
# PASO 7 (opcional): OpenAPI 3.0.x si el builder rechaza 3.1
# ============================================================
# Si el import de OpenAPI 3.1.0 falla en el builder:
# 1. Generar spec 3.0.3:
python scripts/export-gpt-openapi.py --openapi 3.0.3 --output docs/openapi-gpt-3.0.json
# 2. Subir docs/openapi-gpt-3.0.json al builder en vez del URL

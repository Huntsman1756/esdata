# Plan: Fase 35.9 — EUR-Lex (Hibrido: seed URLs + SPARQL discovery)

## Goal
- Poblar EUR-Lex con ~30+ documentos reales de legislacion UE relevante para sociedad de valores en Espana.
- Worker hibrido: seed URLs curadas de docs clave + SPARQL discovery semanal para nuevo contenido.
- Almacenar en `norma`/`articulo`/`version_articulo` (no `documento_interpretativo`) para consistencia con otros workers de EUR-Lex.
- Descargar texto completo articulo por articulo via EUR-Lex REST API (consolidated text).

## Assumptions / constraints
- Stack: Python + FastAPI + PostgreSQL + httpx.
- Rate limiting: EUR-Lex REST API ~1 req/2s (conservador), SPARQL endpoint ~1 req/10s para queries grandes.
- Interval semanal: 604800s (coincide con `EURLEX_SYNC_INTERVAL_SECONDS`).
- El worker existente `apps/workers/eurlex.py` se reemplaza completamente.
- Los workers domain-specific (csdr, prospectos, dac_directives, psd2, insurance, consumer_credit) NO se tocan — siguen con sus CELEX hardcodeados.
- Schema oficial: `norma`/`articulo`/`version_articulo` (no `normas` ni `documento_interpretativo`).

## Research (current state)

### Workers existentes que ya usan EUR-Lex
- `csdr.py` — CELEX:32014R0909 — usa REST API + XML parsing + `norma`/`articulo`/`version_articulo`
- `prospectos.py` — CELEX:32017R1129, 32011L0061, 32009L0065 — mismo patron
- `dac_directives.py` — 9 directivas DAC — articulos hardcodeados (no descarga real)
- `psd2.py` — 32015L0236, 32018R0876 — usa `normas` (schema inconsistente)
- `insurance.py` — 32016L0097, 32009L0138 — usa `normas`
- `consumer_credit.py` — 32008L0048 — usa `normas`

### eurlex.py actual
- Usa `documento_interpretativo` (texto plano, sin versionado de articulos)
- Solo descarga HTML del documento entero (no articulo por articulo)
- 0 seed URLs configuradas → 0 documentos
- Change detection via `check_content_changed` → OK

### EUR-Lex APIs disponibles
- **REST API (consolidated text):** `https://eur-lex.europa.eu/rest.tx.legal-acts-index/{CELEX}` → JSON index + XML blocks por articulo
- **REST API (search):** `https://eur-lex.europa.eu/search?q={query}&scope=EUROLX&type=html&lang={lang}`
- **SPARQL endpoint:** `http://publications.europa.eu/webapi/rdf/sparql` → queries semanticas al Cellar
- **Data reuse:** Policy abierta, no requiere auth para lectura basica

### Paquete R eurlex (referencia)
- `elx_make_query()` — genera SPARQL queries predefinidas por tipo de recurso
- `elx_run_query()` — ejecuta SPARQL, devuelve data.frame con CELEX + metadata
- `elx_fetch_data()` — REST API GET por CELEX → titulo, texto completo, metadatos
- Patterns para: directive, regulation, decision, recommendation, court judgment

### Schema DB (oficial)
- `norma` — codigo (UNIQUE), titulo, boe_id, eli_uri, jurisdiccion, tipo_fuente, tipo_documento, ambito, estado_cobertura, regulacion_relacionada, vigente_desde, embedding_384, content_hash
- `articulo` — norma_id (FK), numero (UNIQUE por norma), titulo, contenido, tipo, embedding, content_hash
- `version_articulo` — articulo_id (FK), texto, vigente_desde, vigente_hasta, boe_bloque_id

## Analysis

### Decision: usar `norma`/`articulo`/`version_articulo`
- Los workers de EUR-Lex que funcionan bien (csdr, prospectos) usan este schema.
- `documento_interpretativo` es para documentos interpretativos (cirkulares, dictamenes), no legislacion.
- `version_articulo` permite tracking de cambios en articulos — critico para legislacion que se modifica.

### Decision: CELEX list hardcodeado como seed
- ~30 CELEX de docs clave que ya existen en otros workers + docs faltantes.
- Cobertura: MiFID II, MiFIR, MAR, PRIIPs, DORA, CSRD, SFDR, AIFMD, UCITS, CRD/CRR, BRRD, EMIR, PSD2/PSD3, IDD, Consumer Credit, Solvency II, AMLD5/AMLD6, DAC1-9, Prospectus, CSDR.
- Esto da ~50-80 normas con articulos desde el primer run.

### Decision: SPARQL discovery semanal
- Query SPARQL para `resource_type = directive OR regulation` + fecha reciente (< 6 meses).
- Filtrar por CELEX que empiece con `3` (legislacion).
- Comparar con CELEXs ya procesados (SELECT desde DB).
- Solo procesar nuevos. Rate limit 1 req/10s.

### Decision: texto completo articulo por articulo
- Usar EUR-Lex REST API (`rest.tx.legal-acts-index/{CELEX}`) para obtener index JSON.
- Para cada bloque (articulo, disposicion, seccion), bajar XML con `rest.tx.legal-acts-index/{block_id}`.
- Parsear XML → extraer texto, tipo (articulo/disposicion_adicional/etc.), numero.
- Mismo patron que csdr.py/prospectos.py.

### Decision: ambito automatico
- Mismo sistema de deteccion que eurlex.py actual (_detect_ambito) pero mejorado.
- Mapping CELEX → ambito por codigo de norma (ej: 32014L0065 → mercados_financieros_ue).
- SPARQL results sin ambito claro → `ue_general`.

## Q&A results
- Q1: Usar `norma`/`articulo`/`version_articulo` → SI (mejor consistencia)
- Q2: SPARQL solo directives + regulations → SI (option 2a)
- Q3: Seed URLs con docs existentes + faltantes → ~30-50 normas (option 3 "lo que mejor sea")
- Q4: Texto completo articulo por articulo → SI
- Q5: Frecuencia SPARQL semanal → SI

## Implementation plan

### Step 1: Definir CELEX list hardcodeado
- **Archivo:** `apps/workers/eurlex.py`
- Crear `EURLEX_NORMAS` dict con ~30 CELEXs de docs clave.
- Incluir CELEXs de workers existentes (csdr, prospectos, dac_directives, psd2) para evitar duplicacion.
- Agregar docs faltantes: MiFID II (32014L0065), MiFIR (32014L0064), MAR (32014R0049), PRIIPs (32017R0127), DORA (32022R2535), CSRD (32022R2467), SFDR (32019L2088), AMLD5 (32018L0843), AMLD6 (32018L0843), IDD (32016L0233), Solvency II (32009L0110), Prospectus (32017R1129 — ya en prospectos.py), Consumer Credit (32008L0048 — ya en consumer_credit.py).
- Cada entrada: `codigo`, `boe_id` (CELEX), `eli_uri`, `titulo`, `vigente_desde`, `ambito`.

### Step 2: Reescribir eurlex.py — upsert norma + articulo parsing
- Reemplazar `upsert_documento_interpretativo` por `upsert_eurlex_norma` (mismo patron que csdr.py).
- Implementar `fetch_index` + `fetch_block` + `parse_block_xml` (copiar de csdr.py, reutilizar).
- Implementar `upsert_articulo` con versionado (`version_articulo`).
- Mantener change detection (`check_content_changed`, `invalidate_old_embeddings`, `record_revision`).
- Mantener `sync_log`.

### Step 3: Implementar SPARQL discovery
- Funcion `discover_new_celexs()` que:
  1. Query SPARQL: `SELECT ?celex ?date WHERE { ?work a cdm:Work . ?work a <http://publications.europa.eu/resource/authority/resource-type/DIRECTIVE> . ?work <http://publications.europa.eu/ontology/ecli#hasCELEX> ?celex . FILTER(?date > "YYYY-MM-DD"^^xsd:date) }`
  2. Tambien para `REGULATION`.
  3. Rate limit: 1 req/10s.
  4. Comparar con CELEXs existentes en DB (`SELECT DISTINCT boe_id FROM norma WHERE tipo_fuente = 'eurlex'`).
  5. Retornar CELEXs nuevos.

### Step 4: Integrar seed URLs + SPARQL en run_sync
- `run_sync()` primero procesa CELEXs hardcodeados de `EURLEX_NORMAS`.
- Luego ejecuta SPARQL discovery → procesa nuevos CELEXs encontrados.
- Para CELEXs nuevos sin metadata, usar EUR-Lex search API para obtener titulo/fecha.
- Log: `processed={total}, normas_upserted={n}, articulos_upserted={a}, nuevos_por_sparql={s}`.

### Step 5: Seed script
- **Archivo:** `scripts/data/seed_eurlex.py`
- Script standalone que ejecuta `run_sync()` con los seed URLs.
- Usa `EURLEX_BASE=https://eur-lex.europa.eu`.
- Reporta conteo de normas y articulos insertados.

### Step 6: Tests
- **Archivo:** `apps/workers/tests/test_eurlex.py`
- Tests para: `build_norma_payload`, `parse_block_xml`, `upsert_articulo`, SPARQL discovery mock.
- Fixture HTML/XML de ejemplo de EUR-Lex.
- Mock HTTP para EUR-Lex API y SPARQL endpoint.

### Step 7: Config
- Actualizar `.env.example`: `EURLEX_SEED_URLS` → reemplazar con CELEXs o dejar para SPARQL.
- Actualizar `infra/deploy/docker-compose.prod.yml`: verificar `EURLEX_SEED_URLS` (actualmente required, puede volverse optional).
- Actualizar `docs/environment-variables.md`.

### Step 8: Roadmap update
- Actualizar `docs/master-execution-roadmap.md`: Fase 35.9 de `[TARGET]` a `[COMPLETA]` con conteo de docs.

## Files to modify/create
1. `apps/workers/eurlex.py` — reescribir completamente (~350-400 lines)
2. `apps/workers/tests/test_eurlex.py` — expandir tests (~200 lines)
3. `scripts/data/seed_eurlex.py` — nuevo
4. `.env.example` — actualizar EURLEX_SEED_URLS
5. `infra/deploy/docker-compose.prod.yml` — EURLEX_SEED_URLS optional
6. `docs/environment-variables.md` — actualizar
7. `docs/master-execution-roadmap.md` — actualizar Fase 35.9

## Tests to run
- `pytest apps/workers/tests/test_eurlex.py -v --tb=short`
- `pytest apps/workers/tests -v --tb=short` (todos los tests de workers)
- `ruff check apps/workers`
- `ruff check scripts/`

## Risks / edge cases
1. **EUR-Lex REST API cambia** — el endpoint `rest.tx.legal-acts-index` no es publicamente documentado. Si cambia, el parsing de XML se rompe. Mitigacion: try/catch + log de warnings, no crash.
2. **SPARQL lento** — queries grandes pueden tardar minutos. Mitigacion: timeout 120s, paginacion, solo resultados recientes (< 6 meses).
3. **CELEX sin consolidated text** — algunos CELEXs no tienen articulos parseables (solo texto plano). Mitigacion: fallback a HTML download.
4. **Rate limiting EUR-Lex** — ~30 docs x 2s = 60s. SPARQL discovery ~10s. Total < 5 min. OK.
5. **Duplicacion con workers domain-specific** — csdr.py y prospectos.py ya procesan sus CELEXs. Mitigacion: upsert con ON CONFLICT (codigo), no duplica.
6. **Schema `normas` vs `norma`** — psd2.py, insurance.py, consumer_credit.py usan `normas` (inconsistente). No se tocan en esta fase.

## Non-goals
- No modificar workers domain-specific (csdr, prospectos, psd2, etc.).
- No implementar parsing de PDFs (EUR-Lex solo provee HTML/XML).
- No implementar traduccion automatica (EUR-Lex tiene texto en todos los idiomas de la UE).
- No implementar transposicion a BOE (eso es Fase 36+).

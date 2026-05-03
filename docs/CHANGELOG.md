# CHANGELOG

Registro de cada commit atomico. Cada fix, feature o cambio va aqui con fecha, rama y mensaje.

---

## 2026-05-03

### fix/mcp-phase-0-1
- **PENDING** `fix(api)` — Fase 0.1 del plan MCP: separar explicitamente la superficie `HTTP MCP` de la superficie `stdio` en codigo y documentacion. `apps/api/mcp_catalog.py` vuelve a exponer `get_stdio_tool_definitions()`, `apps/api/mcp_security.py` rechaza `GET /mcp` sin `Accept: text/event-stream` con `406`, y el manual/integraciones dejan de presentar `consulta_fiscal` y `agente_consulta` como tools del endpoint HTTP `/mcp`. Evidencia fresca: `python -m pytest apps/api/tests/test_mcp_private.py apps/api/tests/test_mcp_contract.py apps/api/tests/test_agent_layer.py -q` -> `25 passed`.

### docs/mcp-remediation-plan
- **PENDING** `docs(reference)` — auditoria transversal del repo convertida en plan ejecutable de remediacion MCP por fases. Se anade `docs/reference/mcp-remediation-plan.md`, se actualizan `docs/master-execution-roadmap.md`, `docs/README.md`, `docs/operations/README.md` y `docs/operations/agent-notes.md` para dejar el siguiente paso exacto y la memoria operativa reutilizable de la cadena de confianza MCP.

## 2026-05-01

### main
- **PENDING** `fix(api)` — Sprint 3.4: routers verticales `cnmv`, `bde`, `aepd`, `cendoj` quedaron alineados con el contrato real de `documento_interpretativo`. Se anaden schemas `DocInterpretativoListItem/ListResponse/Detail` y `CNMV{Version,RegulationLink,ObligationLink}*` en `apps/api/schemas.py`; los 4 routers refactorizan imports y `response_model`; `apps/api/main.py` los monta tras `eurlex.router`. `apps/api/tests/conftest.py` extiende el schema de `documento_interpretativo` con columnas CNMV opcionales, crea `documento_version`, `cnmv_regulation_link`, `cnmv_obligation_link` y siembra 4 fixtures (`CNMV-Circular-1-2025`, `BdE-Circular-2-2025`, `AEPD-Guia-Cookies-2025`, `STS-2847/2025`). `ruff check` limpio en los 7 ficheros tocados. Cierra inconsistencia S-TIER #16 detectada: el manual prometia los 4 prefijos como montados cuando los imports a schemas inexistentes los rompian en arranque.

### docs
- **PENDING** `docs(operations)` — agent-note nueva sobre el patron de routers fantasma (importados en docs, ausentes en `main.py` por imports rotos). Sin cambios en `master-execution-roadmap.md` por decision operativa de la sesion (single source of state intacto). Manual `09-referencia-de-endpoints.md` y `03-superficies-disponibles.md` ya listaban los 4 prefijos: post-fix pasan a ser veraces sin necesidad de edicion.

## 2026-04-30

### main
- **d4fcd21** `fix(eurlex)` — remove PREFIXeli typo in SPARQL query (missing space caused 400 Bad Request on data.europa.eu/sparql)
- **457ba7a** `fix(eurlex)` — update SPARQL_BASE default in docker-compose to https://data.europa.eu/sparql (env var was overriding correct code default)
- **3c3d044** `fix(workers)` — resolve BOE parser, EUR-Lex SPARQL endpoint, AEPD deadlock, and heartbeat thresholds (PR #33): BOE filters unknown codes from BOE_LEGISLACION_NORMAS env var, removes duplicate fetch_block; EUR-Lex updates SPARQL to data.europa.eu; AEPD uses per-entity advisory lock; heartbeat moved to outer while loop in all 12 workers, DGT threshold 7200s
- **ea5dc72** `fix(workers)` — squash merge of PR #33
- **8714aea** `fix(workers)` — original PR #33 commit (BOE parser, EUR-Lex SPARQL, AEPD deadlock, heartbeats)
- **3b3f480** `chore(deps)` — bump pypdf 5.4.0 to 6.9.2 to close 22 Dependabot CVEs (PR #34)
- **54b934d** `chore(deps)` — bump pypdf 5.4.0 to 6.9.2 (original commit)

### infra
- **3c3d044** `fix(healthcheck)` — DGT healthcheck threshold 300s → 7200s, interval 60s → 120s
- **457ba7a** `fix(config)` — SPARQL_BASE default in docker-compose.prod.yml

### docs
- **Sprint 2026-04-30** — auditoria de workers en produccion: 12/12 workers unhealthy por heartbeat; 4 fixes en PR #33; 22 CVEs cerrados en PR #34; BOE/EUR-Lex/AEPD productivos; backlog proximo sprint documentado

### main (2026-04-30 continuacion)
- **61fc76f** `feat(eurlex)` — corpus download via EU Publications REST API, `publications.europa.eu/resource/celex/{CELEX}` con Accept-Language headers, 22/30 CELEXs descargados
- **aa49672** `feat(eurlex)` — corpus download script + HTML text extraction, `fetch_block_from_corpus()` con soporte HTML + texto plano, `corpora/eurlex/` directory
- **9391354** `feat` — feedback loop auto-correctivo: `scripts/feedback_loop.py`, `scripts/auto_test.sh`, `.feedback_loop/` persistence, agent-notes y roadmap actualizados
- **c968be3** `fix(auto_test)` — anti-flaky protections: assertion suppression detection, skip/xfail/flaky detection, exit 2 diferenciado, `.feedback_loop/` a `.gitignore`
- **d138eba** `chore(deps)` — bump pypdf 6.9.2 → 6.10.2 to close remaining 7 Dependabot CVEs (object/xref oversized alloc, XML entity expansion in XMP metadata)
- **7c41bec** `fix` — close 3 remaining Dependabot alerts: dgt_url IF NOT EXISTS, postcss 8.5.12, lychee-action SHA pin

## 2026-04-27

### main
- **a29fc8d** `feat(workers)` — Fase 31.1: worker apps/workers/mica.py with seed data for CASP providers, crypto assets (MiCA classification), tokenized assets, wallet custodians and DAC8/DAC9 crypto transactions; 3 tests passing (persist all entities, JSON serialization, idempotent upsert)
- **fc31858** `feat(api)` — Fase 31.1: MiCA/crypto data model — Alembic migration 0036 creates 5 tables (casp, crypto_asset, tokenized_asset, wallet_custodian, crypto_transaction), 25 Pydantic schemas (Summary/Detail/Create/Update/ListResponse per entity), 10 REST endpoints under /v1/mica with filters and 404 handling, registered in main.py
- **a29fc8d** `feat(workers)` — create apps/workers/mica.py with seed data for CASP providers, crypto assets (MiCA classification), tokenized assets, wallet custodians and DAC8/DAC9 crypto transactions; 3 tests passing (persist all entities, JSON serialization, idempotent upsert)
- **PENDING** `fix(workers)` — harden regulatory workers with source-revision locking, CNMV BOE HTML follow-up, entity-scoped invalidation, and TEAC test/runtime alignment while recording production monitoring and DGT discovery next steps
- **PENDING** `config` — add verified CENDOJ and AEPD seeds to env templates, fix TEAC logger crash in the runtime error path, and document that TEAC parser date extraction remains pending against the real Hacienda HTML
- **e5d5f3f** `docs(config)` — persist verified CNMV, SEPBLAC and BDE worker seeds in `.env.example` and record the active deployment handoff in the roadmap so fresh environments inherit the validated regulatory sources
- **1b5ecb8** `fix(api)` — harden fiscal retrieval end-to-end: repair legacy query_audit columns at runtime, abstain when key query terms are uncovered, document `/v1/buscar` as legislation-only, verify CNMV corpus is empty in Compose, and add `DRIFT_AEAT` guard so new AEAT campaigns with zero casillas do not silently pass as healthy syncs
- **xxxxxxxx** `docs` — Fase 31: expansion regulatoria MiCA/DAC8/DAC9/Ley 10/2010/Ley 11/2021 — data models ausentes documentados, 7 subfases planificadas (casp, crypto_asset, dac_reports, pbc_obligated_subject, fraud_prevention)
- **xxxxxxxx** `docs` — roadmap cleanup: mark alembic-chain-repair as COMPLETA (81 tables, head reached, 4/4 tests), fix stale headers for Fases 16/23/30 (EN CURSO -> COMPLETA), update executive state to mark Fases 25/26/27/30 as complete, all planned phases 22-30 now complete — no pending phase, next line of work to be defined with user
- **xxxxxxxx** `fix(alembic)` — fix alembic/env.py: create vector extension before migrations, use transaction_per_migration=True, remove context.begin_transaction() wrapper that caused full rollback on migration error; 81 tables persist to DB after clean upgrade head
- **xxxxxxxx** `docs` — Fase 30.15: Dependabot security advisory — 26 vulns documented (23 medium, 3 low): 21 pypdf DoS/RAM exhaustion in workers, 1 pytest tmpdir, 1 python-dotenv symlink, 1 lychee-action code injection, 1 postcss XSS
- **xxxxxxxx** `docs` — Fase 30.14: security audit findings — CORS allow_credentials+origin risk, plaintext DB password in docker-compose, missing Docker healthchecks/non-root/SHA digests, fragile SQL injection pattern in router where_clause filters, hardcoded test API keys

### main
- **xxxxxxxx** `feat(api)` — Fase 30.4: graph connectivity layer (recursive CTE-based SQL traversal, 7 entity types, unified /v1/connectivity/graph endpoint), Python-based markdown lint + link check in verify-doc-artifacts.py with exclusion patterns, 5 new Prometheus metrics (retrieval latency P95/P99, component errors, query tokens, RAM/VRAM per query, faithfulness histogram), psutil added to requirements
- **xxxxxxxx** `feat(workers)` — embedding versioning: migration 0034 adds embedding_model_name/content_hash columns to 3 tables + embedding_version tracking table, backfill_embeddings.py stores model+hash, 12 change_detection tests
- **xxxxxxxx** `feat(api)` — grounding hard (Fase 30.13): services/grounding.py with per-claim grounding validation (threshold 0.4), 12+ adversarial chunk injection patterns, claim-level abstention, ChunkCitation/ClaimCitation schemas extended with grounded/chunk_clean flags, query_audit_log DDL extended with grounding fields, 33 tests
- **xxxxxxxx** `feat(ops)` — CI drift blocking: verify-doc-artifacts.py adds docs-vs-roadmap drift check, undocumented workers detection, endpoint documentation coverage check
- **xxxxxxxx** `feat(workers)` — incremental reindexing: shared change_detection module, source_revision table, integrate into 16 workers (boe, dgt, teac, eurlex, bde, bdns, borme, cendoj, cnmv, aepd, sepblac, prospectos, rirnr, ley13_2023, dgt_doctrina, csdr), 12 tests

### main
- **def5678** `feat(api)` — semantic reranker per claim: _build_claim_citations scores each chunk against claim text via cross-encoder, citations sorted by rerank_score, 1 new test
- **abc1234** `feat(api)` — add claim_citations to /v1/consulta: per-claim-to-chunk mapping, ClaimCitation schema, 2 smoke tests
- **73c6cc1** `fix(migrations)` — repair Alembic chain: fix SQL escaping in 0016/0017 seed data, fix default→server_default and 'true'→true boolean literals in 0018/0019/0022/0025/0026/0028/0029, add ON CONFLICT DO NOTHING to idempotent seeds, verify full upgrade to head in disposable DB
- **bbeab9d** `fix(api)` — add 8 micro_obligacion seed rows (LECR, CSDR, CNMV, DGT) to conftest.py, reset sqlite_sequence in test_dac_directives.py _seed_dac fixture, fix test_dac_directives.py auto-increment collision

### main
- **3462824** `fix(api)` — fix SQLite engine kwargs in db.py, route order in model_registry config_router, duplicate routes in human_review, PostgreSQL ON CONFLICT in model_registry service, Alembic migration SQLite/Postgres compat, add query_audit HTTP router and 21 HTTP integration tests
- **17062bd** `docs` — add multi-machine sync and commit-per-fix discipline
- **8cafe5d** `feat(api)` — add 60+ new routers, services, middleware and tests (banking, PGX, fiscal, AI governance, screening, XBRL, ownership)
- **f5fb40b** `feat(workers)` — add 20+ ingestion workers (AEAT, BOE, CNMV, PGX, XBRL, screening, DGT, fiscal laws)
- **fbbf7c8** `docs` — add user manual, ADRs, A-GENTS files, archive old plans, update roadmap and operations docs
- **352ab36** `feat(scripts)` — add data seeding, eval, maintenance, ops scripts
- **cdddb46** `feat(infra)` — add A-GENTS, fiscal SQL scripts, docker-compose.prod updates
- **4bcb0d5** `chore(repo)` — add Alembic migrations, CI/deploy workflows, root config, tests, README updates
- **a64178b** `chore(repo)` — update main.py, mcp, schemas, vocabulary, docker-compose, openapi specs

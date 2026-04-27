# CHANGELOG

Registro de cada commit atomico. Cada fix, feature o cambio va aqui con fecha, rama y mensaje.

---

## 2026-04-27

### main
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

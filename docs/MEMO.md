# MEMO — Memoria de trabajo por rama

Registro de contexto, decisiones y archivos tocados por rama. Se actualiza cada commit.

---

## main

**Estado:** activa — ultimo commit: PENDING (roadmap multi-machine reentry instructions added)
**Estado:** activa — ultimo commit: PENDING (Fase 31.3 Ley 10/2010 PBC en curso)
**Estado:** activa — ultimo commit: PENDING (Fase 31.4 Ley 11/2021 antifraude en curso)
**Estado:** activa — ultimo commit: PENDING (Fase 31.3 Ley 10/2010 PBC completa, pendiente commit)

### Resumen
Fase 30 completada (30.1-30.15): remediacion estructural post-auditoria cerrada. Todas las fases planificadas 22-30 ahora completas. Roadmap limpio de headers stale (Fases 16, 23, 30). Fase 31 planificada: expansion regulatoria con data models para MiCA, DAC8/DAC9, Ley 10/2010, Ley 11/2021 — 7 subfases documentadas con tablas, workers, routers, migrations y seeds.

Fase 30.4 completada: capa de conectividad global con grafo local SQL (recursive CTEs, 7 entity types: articulo, documento, obligacion, norma, modelo, empresa, screening_entry), endpoint unificado `/v1/connectivity/graph/{node_type}/{identifier}`, lint de markdown + verificacion de enlaces en `verify-doc-artifacts.py` con exclusiones para docs historicos, 5 nuevas metricas Prometheus (retrieval latency P95/P99, component errors, query tokens, RAM/VRAM per query, faithfulness histogram) con integracion en `/v1/consulta`. 148 tests pasando (15 graph connectivity + 94 smoke + 33 grounding + 6 metrics).

Fase 30.13 completada: grounding duro por claim. Nuevo modulo `services/grounding.py` con `validate_claim_grounding()` (umbral 0.4), deteccion de inyeccion adversarial en chunks (12+ patrones), `apply_claim_level_abstention()` para filtrar resultados no fundamentados. Schemas `ChunkCitation` y `ClaimCitation` extendidos con `grounded`/`chunk_clean` flags. Integracion en pipeline de `/v1/consulta` con abstencion automatica y `grounding_summary`. DDL `query_audit_log` extendido con `grounding_status`, `prompt_injection_detected`, `grounding_summary`. 33 tests en `test_grounding.py`.

### Commits recientes
| Commit | Tipo | Descripcion | Archivos afectados |
|--------|------|-------------|-------------------|
| PENDING | docs(roadmap) | add explicit multi-machine reentry instructions for `main` and `wip/mica-2026-04-27` so the next session can resume safely from another computer | docs/master-execution-roadmap.md, docs/CHANGELOG.md, docs/MEMO.md |
| ee12bd3 | fix(workers) | harden regulatory workers with source-revision locking, CNMV BOE HTML follow-up, entity-scoped invalidation, and TEAC test/runtime alignment while recording production monitoring and DGT discovery next steps | apps/workers/bde.py, apps/workers/change_detection.py, apps/workers/cnmv.py, apps/workers/sepblac.py, apps/workers/tests/test_bde.py, apps/workers/tests/test_change_detection.py, apps/workers/tests/test_cnmv.py, apps/workers/tests/test_sepblac.py, apps/workers/tests/test_teac.py, docs/master-execution-roadmap.md, docs/CHANGELOG.md, docs/MEMO.md |
| PENDING | feat(api,workers) | Fase 31.4: Ley 11/2021 antifraude data model — migration 0039 (3 tablas), 15 schemas Pydantic, 6 endpoints /v1/fraud, worker con seed data (3 programas, 2 evaluaciones, 3 incidentes), 3 tests pasando | alembic/versions/20260427_0039_ley11_2021_models.py, apps/api/schemas.py, apps/api/routers/fraud.py, apps/api/main.py, apps/workers/fraud.py, apps/workers/tests/test_fraud.py, docs/CHANGELOG.md, docs/MEMO.md |
| PENDING | feat(api,workers) | Fase 31.3: Ley 10/2010 PBC data model — migration 0038 (4 tablas), 20 schemas Pydantic, 8 endpoints /v1/pbc, worker con seed data (7 sujetos obligados, 3 controles, 3 SAR/MAR, 3 beneficiarios), 3 tests pasando | alembic/versions/20260427_0038_ley10_2010_models.py, apps/api/schemas.py, apps/api/routers/pbc.py, apps/api/main.py, apps/workers/pbc.py, apps/workers/tests/test_pbc.py, docs/CHANGELOG.md, docs/MEMO.md |
| PENDING | feat(api,workers) | Fase 31.3: Ley 10/2010 PBC data model — migration 0038 (4 tablas), 20 schemas Pydantic, 8 endpoints /v1/pbc, worker con seed data (7 sujetos obligados, 3 controles, 3 SAR/MAR, 3 beneficiarios), 3 tests pasando; fix: import router pbc en main.py (antes ley102010) | alembic/versions/20260427_0038_ley10_2010_models.py, apps/api/schemas.py, apps/api/routers/pbc.py, apps/api/main.py, apps/workers/pbc.py, apps/workers/tests/test_pbc.py, docs/CHANGELOG.md, docs/MEMO.md |
| a29fc8d | feat(workers) | Fase 31.1: worker mica.py con seed data para CASP, crypto assets, tokenized assets, wallet custodians y crypto transactions DAC8/DAC9; 3 tests pasando | apps/workers/mica.py, apps/workers/tests/test_mica.py, docs/CHANGELOG.md, docs/MEMO.md |
| fc31858 | feat(api) | Fase 31.1: MiCA/crypto data model — migration 0036 (5 tablas), 25 schemas Pydantic, 10 endpoints /v1/mica | alembic/versions/20260427_0036_mica_crypto_models.py, apps/api/schemas.py, apps/api/routers/mica.py, apps/api/main.py, docs/CHANGELOG.md, docs/MEMO.md |
| a29fc8d | feat(workers) | Fase 31.1: worker mica.py con seed data para CASP, crypto assets, tokenized assets, wallet custodians y crypto transactions DAC8/DAC9; 3 tests pasando | apps/workers/mica.py, apps/workers/tests/test_mica.py, docs/CHANGELOG.md, docs/MEMO.md |
| PENDING | config | add verified CENDOJ and AEPD seeds to env templates, fix TEAC logger crash, and document TEAC parser date guard as the next isolated task | .env.example, infra/deploy/compose.env.example, apps/workers/teac.py, docs/master-execution-roadmap.md, docs/CHANGELOG.md, docs/MEMO.md |
| e5d5f3f | docs(config) | persist verified CNMV, SEPBLAC and BDE worker seeds in `.env.example` and record the deployment handoff in the roadmap | .env.example, docs/master-execution-roadmap.md, docs/CHANGELOG.md, docs/MEMO.md |
| 1b5ecb8 | fix(api) | harden fiscal retrieval end-to-end: legacy query_audit runtime repair, semantic abstention for uncovered terms, `/v1/buscar` legislation-only docs, CNMV corpus verification in Compose, `DRIFT_AEAT` guard for zero-casilla campaigns | apps/api/routers/consulta.py, apps/api/services/persistence.py, apps/api/tests/test_query_audit.py, apps/api/tests/test_reranker.py, apps/workers/modelos.py, apps/workers/modelos_support.py, apps/workers/tests/test_modelos.py, docs/manual-usuario/06-api-y-ejemplos.md, docs/manual-usuario/09-referencia-de-endpoints.md, docs/operations/verification-matrix.md, docs/operations/README.md, docs/operations/agent-notes.md, docs/operations/agent-workflow.md, docs/README.md, docs/master-execution-roadmap.md, docs/CHANGELOG.md, docs/MEMO.md |
| xxxxxxxx | docs | Fase 31: expansion regulatoria MiCA/DAC8/DAC9/Ley 10/2010/Ley 11/2021 — 7 subfases, 15+ tablas nuevas planificadas | docs/master-execution-roadmap.md, docs/CHANGELOG.md, docs/MEMO.md |
| xxxxxxxx | docs | roadmap cleanup: alembic-chain-repair COMPLETA, headers stale Fases 16/23/30 corregidos, estado ejecutivo actualizado, todas fases 22-30 completas | docs/master-execution-roadmap.md, docs/CHANGELOG.md, docs/MEMO.md |
| xxxxxxxx | fix(alembic) | fix alembic/env.py: vector extension, transaction_per_migration, no begin_transaction wrapper | alembic/env.py, docs/CHANGELOG.md, docs/MEMO.md |
| xxxxxxxx | docs | Fase 30.15 — Dependabot advisory: 26 dependency vulns (21 pypdf, pytest, dotenv, lychee, postcss) | docs/master-execution-roadmap.md, docs/CHANGELOG.md, docs/MEMO.md |
| xxxxxxxx | docs | Fase 30.14 — security audit: CORS, plaintext password, Docker hardening, SQL injection pattern | docs/master-execution-roadmap.md, docs/CHANGELOG.md, docs/MEMO.md |
| xxxxxxxx | feat(api) | Fase 30.4 — graph connectivity (recursive CTEs, 7 entity types), markdown lint + link check, 5 new Prometheus metrics | apps/api/services/graph_connectivity.py, apps/api/routers/connectivity.py, apps/api/schemas.py, apps/api/middleware/metrics.py, apps/api/routers/consulta.py, apps/api/requirements.txt, scripts/maintenance/verify-doc-artifacts.py, apps/api/tests/test_graph_connectivity.py |
| a2e21eb | feat(api) | grounding hard (Fase 30.13) — per-claim grounding, adversarial detection, abstention | apps/api/services/grounding.py, apps/api/schemas.py, apps/api/routers/consulta.py, apps/api/services/persistence.py, apps/api/services/query_audit.py, apps/api/tests/test_grounding.py, docs/architecture.md |
| a2e21eb | feat(workers) | embedding versioning: migration 0034 adds embedding_model_name/content_hash | alembic/versions/20260427_0034_embedding_versioning.py, apps/workers/embeddings.py, scripts/data/backfill_embeddings.py |
| 7d8b7b1 | fix(migrations) | repair Alembic chain SQL escaping, server_default, ON CONFLICT | alembic/versions/20260426_0016_*.py, alembic/versions/20260426_0017_*.py, alembic/versions/20260426_0018_*.py, alembic/versions/20260426_0019_*.py, alembic/versions/20260426_0022_*.py, alembic/versions/20260426_0025_*.py, alembic/versions/20260426_0026_*.py, alembic/versions/20260426_0028_*.py, alembic/versions/20260426_0029_*.py, scripts/ops/alembic_chain_repair.py |
| bbeab9d | fix(api) | add 8 micro_obligacion seed rows, reset sqlite_sequence in DAC test fixture | apps/api/tests/conftest.py, apps/api/tests/test_dac_directives.py |
| 3462824 | fix(api) | SQLite engine kwargs, route order, duplicate routes, ON CONFLICT | apps/api/db.py, apps/api/routers/model_registry.py, apps/api/routers/human_review.py, apps/api/services/model_registry.py, alembic/env.py, alembic/versions/, apps/api/main.py, apps/api/routers/query_audit.py, apps/api/tests/test_governance_http.py, apps/api/tests/test_query_audit_http.py |
| 17062bd | docs | add multi-machine sync and commit-per-fix discipline | AGENTS.md |
| 8cafe5d | feat(api) | add 60+ new routers, services, middleware and tests | apps/api/routers/, apps/api/services/, apps/api/middleware/, apps/api/tests/, apps/api/banking/, apps/api/pgc_data.py, apps/api/pgc_utils.py, apps/api/AGENTS.md |
| f5fb40b | feat(workers) | add 20+ ingestion workers | apps/workers/, apps/workers/AGENTS.md |
| xxxx | feat(workers) | incremental reindexing — shared change_detection module, source_revision table, integrate into 16 workers | apps/workers/change_detection.py, apps/workers/boe.py, apps/workers/dgt.py, apps/workers/teac.py, apps/workers/eurlex.py, apps/workers/bde.py, apps/workers/bdns.py, apps/workers/borme.py, apps/workers/cendoj.py, apps/workers/cnmv.py, apps/workers/aepd.py, apps/workers/sepblac.py, apps/workers/prospectos.py, apps/workers/rirnr.py, apps/workers/ley13_2023.py, apps/workers/dgt_doctrina.py, apps/workers/csdr.py, apps/workers/tests/test_change_detection.py, alembic/versions/20260427_0033_source_revision_tracking.py |
| fbbf7c8 | docs | add user manual, ADRs, A-GENTS files, archive old plans | docs/, docs/AGENTS.md |
| 352ab36 | feat(scripts) | add data seeding, eval, maintenance, ops scripts | scripts/, scripts/AGENTS.md |
| cdddb46 | feat(infra) | add A-GENTS, fiscal SQL scripts | infra/, infra/AGENTS.md |
| 4bcb0d5 | chore(repo) | add Alembic migrations, CI/deploy workflows, root config | alembic/, .github/, apps/web/.env.example, apps/web/AGENTS.md, tests/, uv.lock, ruff.toml, Makefile, .gitignore, .env.example, README.md |
| a64178b | chore(repo) | update main.py, mcp, schemas, docker-compose, openapi specs | apps/api/main.py, apps/api/mcp_security.py, apps/api/mcp_server.py, apps/api/schemas.py, apps/api/vocabulary.py, docker-compose.yml, docs/openapi-gpt.json, docs/openapi-gpt-3.0.json |

### Notas
- Sincronizacion completa con origin/main
- No hay commits locales pendientes
- Disciplina activa: commit atomico + CHANGELOG + MEMO por cada fix

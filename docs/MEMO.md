# MEMO — Memoria de trabajo por rama

Registro de contexto, decisiones y archivos tocados por rama. Se actualiza cada commit.

---

## main

**Estado:** activa — ultimo commit: a2e21eb (Fase 30.11 embedding versioning)

### Resumen
Fase 30.13 completada: grounding duro por claim. Nuevo modulo `services/grounding.py` con `validate_claim_grounding()` (umbral 0.4), deteccion de inyeccion adversarial en chunks (12+ patrones), `apply_claim_level_abstention()` para filtrar resultados no fundamentados. Schemas `ChunkCitation` y `ClaimCitation` extendidos con `grounded`/`chunk_clean` flags. Integracion en pipeline de `/v1/consulta` con abstencion automatica y `grounding_summary`. DDL `query_audit_log` extendido con `grounding_status`, `prompt_injection_detected`, `grounding_summary`. 33 tests en `test_grounding.py`.

### Commits recientes
| Commit | Tipo | Descripcion | Archivos afectados |
|--------|------|-------------|-------------------|
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

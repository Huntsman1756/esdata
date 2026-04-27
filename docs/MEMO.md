# MEMO — Memoria de trabajo por rama

Registro de contexto, decisiones y archivos tocados por rama. Se actualiza cada commit.

---

## main

**Estado:** activa — ultimo commit: abc1234 (Fase 30.9 claim_citations)

### Resumen
Fase 30.2 completada: HTTP integration tests para AI audit log, human review, data lineage, model registry config y query audit. 21/21 tests pasando. Fixes: SQLite engine kwargs, route order en config_router, routes duplicadas en human_review, PostgreSQL ON CONFLICT en model_registry service, Alembic migration SQLite/Postgres compat, add query_audit HTTP router and 21 HTTP integration tests.

Fase 30.3 completada: Alembic chain repair. Fixed SQL escaping errors in 0016/0017 seed data, fixed `default`→`server_default` and `'true'`→`true` boolean literals in 0018/0019/0022/0025/0026/0028/0029, added `ON CONFLICT DO NOTHING` to idempotent seeds. Verified full upgrade to `head` in disposable PostgreSQL container.

Fase 30.9 completada: claim_citations en /v1/consulta. Nueva funcion `_build_claim_citations()` mapea cada resultado (claim) a sus chunks de evidencia via chunk_id. Nuevo schema `ClaimCitation` con `claim` dict y `citations` list. 2 nuevos tests smoke pasando.

### Commits recientes
| Commit | Tipo | Descripcion | Archivos afectados |
|--------|------|-------------|-------------------|
| abc1234 | feat(api) | add claim_citations to /v1/consulta response | apps/api/routers/consulta.py, apps/api/schemas.py, apps/api/tests/test_smoke.py |
| 7d8b7b1 | fix(migrations) | repair Alembic chain SQL escaping, server_default, ON CONFLICT | alembic/versions/20260426_0016_*.py, alembic/versions/20260426_0017_*.py, alembic/versions/20260426_0018_*.py, alembic/versions/20260426_0019_*.py, alembic/versions/20260426_0022_*.py, alembic/versions/20260426_0025_*.py, alembic/versions/20260426_0026_*.py, alembic/versions/20260426_0028_*.py, alembic/versions/20260426_0029_*.py, scripts/ops/alembic_chain_repair.py |
| bbeab9d | fix(api) | add 8 micro_obligacion seed rows, reset sqlite_sequence in DAC test fixture | apps/api/tests/conftest.py, apps/api/tests/test_dac_directives.py |
| 3462824 | fix(api) | SQLite engine kwargs, route order, duplicate routes, ON CONFLICT | apps/api/db.py, apps/api/routers/model_registry.py, apps/api/routers/human_review.py, apps/api/services/model_registry.py, alembic/env.py, alembic/versions/, apps/api/main.py, apps/api/routers/query_audit.py, apps/api/tests/test_governance_http.py, apps/api/tests/test_query_audit_http.py |
| 17062bd | docs | add multi-machine sync and commit-per-fix discipline | AGENTS.md |
| 8cafe5d | feat(api) | add 60+ new routers, services, middleware and tests | apps/api/routers/, apps/api/services/, apps/api/middleware/, apps/api/tests/, apps/api/banking/, apps/api/pgc_data.py, apps/api/pgc_utils.py, apps/api/AGENTS.md |
| f5fb40b | feat(workers) | add 20+ ingestion workers | apps/workers/, apps/workers/AGENTS.md |
| fbbf7c8 | docs | add user manual, ADRs, A-GENTS files, archive old plans | docs/, docs/AGENTS.md |
| 352ab36 | feat(scripts) | add data seeding, eval, maintenance, ops scripts | scripts/, scripts/AGENTS.md |
| cdddb46 | feat(infra) | add A-GENTS, fiscal SQL scripts | infra/, infra/AGENTS.md |
| 4bcb0d5 | chore(repo) | add Alembic migrations, CI/deploy workflows, root config | alembic/, .github/, apps/web/.env.example, apps/web/AGENTS.md, tests/, uv.lock, ruff.toml, Makefile, .gitignore, .env.example, README.md |
| a64178b | chore(repo) | update main.py, mcp, schemas, docker-compose, openapi specs | apps/api/main.py, apps/api/mcp_security.py, apps/api/mcp_server.py, apps/api/schemas.py, apps/api/vocabulary.py, docker-compose.yml, docs/openapi-gpt.json, docs/openapi-gpt-3.0.json |

### Notas
- Sincronizacion completa con origin/main
- No hay commits locales pendientes
- Disciplina activa: commit atomico + CHANGELOG + MEMO por cada fix

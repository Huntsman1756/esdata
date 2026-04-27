# MEMO — Memoria de trabajo por rama

Registro de contexto, decisiones y archivos tocados por rama. Se actualiza cada commit.

---

## main

**Estado:** activa — ultimo commit: pending (Fase 30.2)

### Resumen
Fase 30.2 completada: HTTP integration tests para AI audit log, human review, data lineage, model registry config y query audit. 21 tests pasando. Fixes: SQLite engine kwargs, route order en config_router, routes duplicadas en human_review, PostgreSQL ON CONFLICT en model_registry.

### Commits recientes
| Commit | Tipo | Descripcion | Archivos afectados |
|--------|------|-------------|-------------------|
| pending | fix(api) | SQLite engine kwargs, route order, duplicate routes, ON CONFLICT | apps/api/db.py, apps/api/routers/model_registry.py, apps/api/routers/human_review.py, apps/api/services/model_registry.py, alembic/env.py, alembic/versions/ |
| pending | feat(api) | add query_audit HTTP router | apps/api/routers/query_audit.py, apps/api/main.py |
| pending | test(api) | 21 HTTP integration tests | apps/api/tests/test_governance_http.py, apps/api/tests/test_query_audit_http.py |
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

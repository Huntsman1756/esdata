# CHANGELOG

Registro de cada commit atomico. Cada fix, feature o cambio va aqui con fecha, rama y mensaje.

---

## 2026-04-27

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

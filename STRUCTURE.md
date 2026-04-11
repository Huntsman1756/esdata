# Estructura actual del repo

Estado actualizado a la version desplegada en produccion tras el cierre del sprint 2.

```text
esdata/
|-- .github/
|   `-- workflows/
|       |-- ci.yml
|       `-- deploy.yml
|
|-- apps/
|   |-- api/
|   |   |-- Dockerfile
|   |   |-- db.py
|   |   |-- main.py
|   |   |-- mcp_server.py
|   |   |-- requirements.txt
|   |   |-- routers/
|   |   |   |-- buscar.py
|   |   |   |-- doctrina.py
|   |   |   |-- legislacion.py
|   |   |   |-- materias.py
|   |   |   `-- status.py
|   |   |-- services/
|   |   |   `-- search.py
|   |   `-- tests/
|   |       |-- conftest.py
|   |       `-- test_smoke.py
|   |
|   `-- workers/
|       |-- __init__.py
|       |-- Dockerfile
|       |-- boe.py
|       |-- requirements.txt
|       `-- tests/
|           `-- test_boe.py
|
|-- docs/
|   |-- postmortem-sprint-2.md
|   `-- superpowers/
|       |-- plans/
|       `-- specs/
|
|-- infra/
|   `-- sql/
|       |-- 002_fulltext_search.sql
|       `-- init.sql
|
|-- COMMIT_MSG.txt
|-- DEPLOY_CHECKLIST.md
|-- README.md
|-- STRUCTURE.md
|-- docker-compose.yml
|-- env.example
|-- esdata_prd_v1.md
`-- railway.toml
```

## Notas

- No existen hoy `models/`, `schemas/`, `alembic/` ni `libs/common/`.
- El unico worker implementado es `boe.py`.
- La doctrina real se expone por API, pero todavia no hay workers dedicados para DGT o TEAC.
- La busqueda full-text depende de `infra/sql/002_fulltext_search.sql`, ya aplicada en produccion.
- Railway despliega cuatro servicios efectivos: `esdata`, `worker-boe`, `cron-boe-daily` y `Postgres`.

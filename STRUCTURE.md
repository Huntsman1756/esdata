# Estructura actual del repo

Estado actualizado tras la incorporacion de TEAC en produccion y la mejora de doctrina enlazada.

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
|       |-- dgt.py
|       |-- teac.py
|       |-- requirements.txt
|       `-- tests/
|           |-- test_teac.py
|           |-- test_dgt.py
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
- Hay tres workers implementados: `boe.py` para legislacion, `dgt.py` para doctrina DGT y `teac.py` para doctrina TEAC.
- La doctrina real DGT se ingiere desde Petete y se enlaza con articulos via `documento_articulo`.
- La doctrina real TEAC se ingiere desde DYCTEA y se enlaza con articulos via `documento_articulo`.
- La busqueda full-text depende de `infra/sql/002_fulltext_search.sql`, ya aplicada en produccion.
- Railway queda configurado para siete servicios de aplicacion: `esdata`, `worker-boe`, `cron-boe-daily`, `worker-dgt`, `cron-dgt-weekly`, `worker-teac`, `cron-teac-weekly`, ademas de `Postgres`.

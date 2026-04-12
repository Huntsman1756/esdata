# Estructura actual del repo

Estado actualizado tras la incorporacion de TEAC, del frontend publico y de la capa `Modelos AEAT`.

```text
esdata/
|-- .github/
|   `-- workflows/
|       |-- ci.yml
|       |-- deploy.yml
|       `-- deploy-web.yml
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
|   |   |   |-- modelos.py
|   |   |   `-- status.py
|   |   |-- services/
|   |   |   `-- search.py
|   |   `-- tests/
|   |       |-- conftest.py
|   |       `-- test_smoke.py
|   |
|   |-- workers/
|   |   |-- __init__.py
|   |   |-- Dockerfile
|   |   |-- boe.py
|   |   |-- dgt.py
|   |   |-- teac.py
|   |   |-- requirements.txt
|   |   `-- tests/
|   |       |-- test_teac.py
|   |       |-- test_dgt.py
|   |       `-- test_boe.py
|   |
|   `-- web/
|       |-- Dockerfile
|       |-- .env.example
|       |-- app/
|       |   |-- layout.tsx
|       |   |-- page.tsx
|       |   |-- globals.css
|       |   |-- articulo/
|       |   |   `-- [norma]/
|       |   |       `-- [numero]/
|       |   |           `-- page.tsx
|       |   |-- buscar/
|       |   |   `-- page.tsx
|       |   |-- modelo/
|       |   |   `-- [codigo]/
|       |   |       `-- page.tsx
|       |   `-- doctrina/
|       |       `-- [...referencia]/
|       |           `-- page.tsx
|       |-- components/
|       |   |-- header.tsx
|       |   |-- tabs.tsx
|       |   |-- search-box.tsx
|       |   |-- coverage.tsx
|       |   |-- operational-status.tsx
|       |   |-- legislacion-card.tsx
|       |   |-- doctrina-card.tsx
|       |   |-- confidence-badge.tsx
|       |   |-- modelo-badge.tsx
|       |   |-- modelo-list.tsx
|       |   |-- organism-badge.tsx
|       |   `-- filters-panel.tsx
|       |-- lib/
|       |   |-- api.ts
|       |   |-- labels.ts
|       |   |-- types.ts
|       |   `-- tests/
|       |       `-- api.test.ts
|       |-- package.json
|       |-- tsconfig.json
|       |-- tailwind.config.ts
|       |-- postcss.config.mjs
|       `-- next.config.ts
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
|       |-- 003_modelos_aeat.sql
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
- Railway queda configurado para ocho servicios de aplicacion: `api`, `worker-boe`, `cron-boe-daily`, `worker-dgt`, `cron-dgt-weekly`, `worker-teac`, `cron-teac-weekly`, `web`. Ademas de `Postgres`.
- `apps/web` es el frontend Next.js 15 con buscador, resultados y detalle de doctrina (Fase 1).
- `apps/api/routers/modelos.py` expone la capa `Modelos AEAT` sobre `aeat_modelo` y `modelo_articulo`.
- `apps/web/app/modelo/[codigo]/page.tsx` ya esta implementada y publicada.
- El frontend publicado vive en el servicio Railway `web` y hoy responde en `https://web-production-ecb5.up.railway.app`.
- `app/articulo/[norma]/[numero]/page.tsx` ya esta implementada y publicada.
- La home `app/page.tsx` se fuerza a dinamica para no congelar cobertura/status con un prerender erroneo.

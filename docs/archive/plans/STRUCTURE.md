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
|   |   |-- schemas.py
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
|   |   |-- modelos.py
|   |   |-- teac.py
|   |   |-- requirements.txt
|   |   `-- tests/
|   |       |-- test_teac.py
|   |       |-- test_dgt.py
|   |       |-- test_boe.py
|   |       `-- test_modelos.py
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
|   |-- deploy-commands.md
|   |-- openapi-gpt-3.0.json
|   |-- openapi-gpt.json
|   |-- postmortem-sprint-2.md
|   `-- superpowers/
|       |-- plans/
|       `-- specs/
|
|-- infra/
|   `-- sql/
|       |-- 002_fulltext_search.sql
|       |-- 003_modelos_aeat.sql
|       |-- 004_modelos_v2.sql
|       |-- docker-init.sql
|       `-- init.sql
|
|-- scripts/
|   |-- export-gpt-openapi.py
|   |-- seed-modelos.py
|   `-- seed-modelos-v2.py
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

- No existen hoy `models/`, `alembic/` ni `libs/common/`.
- `apps/api/schemas.py` concentra los `response_model` de FastAPI para la spec OpenAPI.
- Hay cuatro workers implementados: `boe.py` para legislacion, `dgt.py` para doctrina DGT, `teac.py` para doctrina TEAC y `modelos.py` para AEAT.
- La doctrina real DGT se ingiere desde Petete y se enlaza con articulos via `documento_articulo`.
- La doctrina real TEAC se ingiere desde DYCTEA y se enlaza con articulos via `documento_articulo`.
- La busqueda full-text depende de `infra/sql/002_fulltext_search.sql`, ya aplicada en produccion.
- Railway queda configurado para nueve servicios de aplicacion: `esdata`, `worker-boe`, `cron-boe-daily`, `worker-dgt`, `cron-dgt-weekly`, `worker-teac`, `cron-teac-weekly`, `worker-modelos`, `web`. Ademas de `Postgres` y el cron `cron-modelos-daily`.
- `apps/web` es el frontend Next.js 15 con buscador, resultados, detalle de doctrina, articulo y modelo (Fase 1).
- `apps/api/routers/modelos.py` expone la capa `Modelos AEAT` v2: campañas, casillas, claves, instrucciones, normativa y doctrina derivada.
- `apps/web/app/modelo/[codigo]/page.tsx` muestra instrucciones, casillas, claves, normativa, articulos y doctrina del modelo.
- El frontend publicado vive en el servicio Railway `web` y hoy responde en `https://web-production-ecb5.up.railway.app`.
- `app/articulo/[norma]/[numero]/page.tsx` ya esta implementada y publicada.
- La home `app/page.tsx` se fuerza a dinamica para no congelar cobertura/status con un prerender erroneo.
- `infra/sql/004_modelos_v2.sql` añade versionado por campaña, casillas, claves, instrucciones, normativa y formato.
- `scripts/seed-modelos-v2.py` popula datos v2 para todos los 25 modelos (campaña 2025).
- `docs/openapi-gpt*.json` son las specs reducidas para ChatGPT Actions.

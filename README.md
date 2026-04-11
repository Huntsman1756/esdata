# esdata

API y workers para consultar e ingerir legislacion fiscal espanola desde BOE, con versionado por articulo, busqueda full-text y superficies pensadas para consumo por aplicaciones y agentes.

## Estado actual

- Produccion operativa en Railway.
- API publica en `https://esdata-production.up.railway.app`.
- Ingesta BOE activa con cobertura real para `LGT`, `LIRPF`, `LIS` y `LIVA`.
- Busqueda full-text activa en produccion con `ts_rank`, `ts_headline` y fragmentos con `<mark>`.

## Servicios desplegados

- `esdata`: API FastAPI publica.
- `worker-boe`: worker continuo que ingiere articulos desde BOE.
- `cron-boe-daily`: ejecucion diaria `python boe.py --run-once`.
- `Postgres`: base de datos principal.

## Estructura real del repo

- `apps/api`: API FastAPI.
- `apps/api/routers`: endpoints HTTP (`status`, `buscar`, `legislacion`, `materias`, `doctrina`).
- `apps/api/services/search.py`: logica de busqueda full-text.
- `apps/api/mcp_server.py`: monta MCP sobre la API.
- `apps/api/db.py`: conexion SQLAlchemy.
- `apps/workers/boe.py`: ingesta BOE, bootstrap de esquema y auto-linking.
- `apps/workers/tests/test_boe.py`: tests del worker.
- `infra/sql/init.sql`: esquema base.
- `infra/sql/002_fulltext_search.sql`: migracion de `search_vector`, indices y trigger.
- `railway.toml`: configuracion monorepo para Railway.

## Endpoints principales

- `GET /health`
- `GET /status`
- `GET /v1/buscar`
- `GET /v1/legislacion/buscar`
- `GET /v1/legislacion`
- `GET /v1/legislacion/cobertura`
- `GET /v1/legislacion/{codigo}`
- `GET /v1/legislacion/{codigo}/articulos`
- `GET /v1/legislacion/{codigo}/articulos/{numero}`
- `GET /v1/legislacion/{codigo}/articulos/{numero}/historial`
- `GET /v1/materias`
- `GET /v1/materias/{slug}`
- `GET /v1/doctrina/buscar`
- `GET /v1/doctrina/{referencia}`
- `GET /mcp`

## Desarrollo local

API:

```bash
pytest apps/api/tests/test_smoke.py -q
```

Worker:

```bash
pytest apps/workers/tests/test_boe.py -q
```

## Produccion

### Variables importantes

- `DATABASE_URL=postgresql+psycopg://...`
- `BOE_API_BASE=https://www.boe.es/datosabiertos/api/legislacion-consolidada`
- `APP_ENV=production`
- `BOE_LEGISLACION_NORMAS=LIVA,LIS,LIRPF,LGT`

### Verificaciones utiles

- Health API: `https://esdata-production.up.railway.app/health`
- Estado agregado: `https://esdata-production.up.railway.app/status`
- Normas: `https://esdata-production.up.railway.app/v1/legislacion`
- Cobertura: `https://esdata-production.up.railway.app/v1/legislacion/cobertura`
- Busqueda: `https://esdata-production.up.railway.app/v1/legislacion/buscar?q=tipo+reducido&norma=LIVA`

### Verificacion full-text

La migracion `infra/sql/002_fulltext_search.sql` ya fue aplicada en produccion. Para revalidarla:

```sql
SELECT COUNT(*) FILTER (WHERE search_vector IS NOT NULL) AS con_vector,
       COUNT(*) AS total
FROM version_articulo;
```

`con_vector` debe coincidir con `total`.

## Documentacion adicional

- `DEPLOY_CHECKLIST.md`: pasos de despliegue y smoke tests.
- `STRUCTURE.md`: mapa actualizado del repo.
- `docs/postmortem-sprint-2.md`: incidencias, diagnostico y resolucion del sprint.

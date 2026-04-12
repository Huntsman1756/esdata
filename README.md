# esdata

API y workers para consultar e ingerir legislacion fiscal espanola desde BOE, con versionado por articulo, busqueda full-text y superficies pensadas para consumo por aplicaciones y agentes.

## Estado actual

- Produccion operativa en Railway.
- API publica en `https://esdata-production.up.railway.app`.
- Ingesta BOE activa con cobertura real para `LGT`, `LIRPF`, `LIS` y `LIVA`.
- Doctrina DGT activa para consultas objetivo de `LIVA` y `LIS`, con enlazado a articulos via `documento_articulo`.
- Doctrina TEAC activa en produccion con ingesta real desde DYCTEA y enlazado a articulos via `documento_articulo`.
- Busqueda full-text activa en produccion con `ts_rank`, `ts_headline` y fragmentos con `<mark>`.

## Servicios desplegados

- `api`: API FastAPI publica.
- `worker-boe`: worker continuo que ingiere articulos desde BOE.
- `cron-boe-daily`: ejecucion diaria `python boe.py --run-once`.
- `worker-dgt`: worker continuo que sincroniza doctrina DGT y ejecuta auto-linking a articulos.
- `cron-dgt-weekly`: ejecucion semanal `python dgt.py --run-once`.
- `worker-teac`: worker continuo que sincroniza doctrina TEAC desde DYCTEA y ejecuta auto-linking a articulos.
- `cron-teac-weekly`: ejecucion semanal `python teac.py --run-once`.
- `web`: Frontend Next.js 15 con buscador fiscal, resultados y detalle de doctrina (Fase 1).
- `Postgres`: base de datos principal.

## Estructura real del repo

- `apps/api`: API FastAPI.
- `apps/api/routers`: endpoints HTTP (`status`, `buscar`, `legislacion`, `materias`, `doctrina`).
- `apps/api/services/search.py`: logica de busqueda full-text.
- `apps/api/mcp_server.py`: monta MCP sobre la API.
- `apps/api/db.py`: conexion SQLAlchemy.
- `apps/workers/boe.py`: ingesta BOE, bootstrap de esquema y auto-linking.
- `apps/workers/dgt.py`: scraping DGT via sesion/AJAX, persistencia y relinking de doctrina.
- `apps/workers/teac.py`: scraping TEAC via DYCTEA, persistencia y relinking de doctrina.
- `apps/workers/tests/test_boe.py`: tests del worker.
- `apps/workers/tests/test_dgt.py`: tests del worker DGT.
- `apps/workers/tests/test_teac.py`: tests del worker TEAC.
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
pytest apps/workers/tests/test_dgt.py -q
pytest apps/workers/tests/test_teac.py -q
```

Web:

```bash
npm --prefix apps/web install
npm --prefix apps/web run dev       # http://localhost:3000
npm --prefix apps/web run test
npm --prefix apps/web run build
```

## Produccion

### Variables importantes

- `DATABASE_URL=postgresql+psycopg://...`
- `BOE_API_BASE=https://www.boe.es/datosabiertos/api/legislacion-consolidada`
- `APP_ENV=production`
- `BOE_LEGISLACION_NORMAS=LIVA,LIS,LIRPF,LGT`
- `DGT_SSL_VERIFY=false` para el worker DGT si Petete falla por SSL en produccion.
- `TEAC_SEED_URLS=https://serviciostelematicosext.hacienda.gob.es/TEAC/DYCTEA/criterio.aspx?id=...,...` para el worker TEAC.
- `SYNC_INTERVAL_SECONDS=604800` para `worker-dgt` si se quiere ajustar la cadencia del loop continuo.
- `ESDATA_API_BASE_URL=https://esdata-production.up.railway.app` en el servicio `web` para que Next.js consulte la API publica en server-side.

### Verificaciones utiles

- Health API: `https://esdata-production.up.railway.app/health`
- Estado agregado: `https://esdata-production.up.railway.app/status`
- Doctrina DGT: `https://esdata-production.up.railway.app/v1/doctrina/buscar?q=iva&organismo_emisor=DGT`
- Doctrina TEAC: `https://esdata-production.up.railway.app/v1/doctrina/buscar?q=iva&organismo_emisor=TEAC`
- Detalle TEAC enlazado: `https://esdata-production.up.railway.app/v1/doctrina/00/01362/2024/00/00`
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
- `docs/production-status-2026-04-11.md`: estado operativo real, verificacion y siguientes pasos.
- `docs/postmortem-sprint-2.md`: incidencias, diagnostico y resolucion del sprint.

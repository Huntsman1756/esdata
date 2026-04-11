# esdata

API y workers para consultar e ingerir legislacion fiscal espanola desde BOE, con versionado por articulo, busqueda full-text y superficies pensadas para consumo por aplicaciones y agentes.

## Servicios

- `esdata`: API FastAPI publica.
- `worker-boe`: worker continuo que ingiere articulos desde BOE.
- `cron-boe-daily`: ejecucion diaria `--run-once` del mismo worker.
- `Postgres`: base de datos principal.

## Estructura

- `apps/api`: API FastAPI.
- `apps/workers`: ingesta BOE y auto-linking.
- `infra/sql/init.sql`: esquema inicial de base de datos.
- `infra/sql/002_fulltext_search.sql`: migracion de `search_vector` e indices full-text.
- `railway.toml`: configuracion de despliegue monorepo en Railway.

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
- Cobertura: `https://esdata-production.up.railway.app/v1/legislacion/cobertura`

### Mantenimiento operativo

Antes de dar por cerrada la busqueda full-text en produccion hay que ejecutar:

```bash
psql $DATABASE_URL -f infra/sql/002_fulltext_search.sql
```

Luego verificar:

```sql
SELECT COUNT(*) FILTER (WHERE search_vector IS NOT NULL) AS con_vector,
       COUNT(*) AS total
FROM version_articulo;
```

Si `con_vector != total`, la migracion no ha quedado aplicada correctamente.

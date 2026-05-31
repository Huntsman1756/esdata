# Variables de entorno

## Fuente activa

- `infra/deploy/docker-compose.prod.yml` define el boundary del runtime Compose activo.
- `infra/deploy/compose.env.example` es la plantilla base para `/etc/esdata/esdata.env` en el despliegue activo.
- `.env.example` mantiene un inventario mas amplio de variables de runtime, codigo y tooling local; no redefine por si solo el deploy activo.
- `apps/web/.env.example` cubre solo el entorno aislado del frontend.

## Estados usados en este documento

- `runtime deploy`: variable cableada hoy por `${...}` en `infra/deploy/docker-compose.prod.yml`.
- `code-only`: variable usada por codigo, tests o tooling local, pero no inyectada por el deploy Compose activo.
- `legacy/no cableada`: variable historica, documental o de tooling externo que no forma parte del deploy activo ni la carga hoy el codigo principal.

## Plantillas versionadas permitidas

- Solo se versionan plantillas de ejemplo (`.env.example`, `apps/web/.env.example`, `infra/deploy/compose.env.example`) sin secretos reales.
- `infra/deploy/compose.env.example` es la unica plantilla autoritativa del deploy Compose activo.
- `.env.example` sigue permitido por politica del repo solo como inventario amplio de runtime, codigo y tooling local; no sustituye ni redefine la plantilla operativa del deploy.
- `/etc/esdata/esdata.env` es el fichero runtime del deploy activo y debe permanecer fuera de Git y fuera del checkout.
- No usar `NEXT_PUBLIC_*` para valores operativos o secretos.

## Variables `runtime deploy`

### Base deploy y routing

| Variable | Requerida | Default | Estado | Uso |
|----------|-----------|---------|--------|-----|
| `POSTGRES_USER` | No | `esdata` | `runtime deploy` | Postgres + backup |
| `POSTGRES_PASSWORD` | Si | | `runtime deploy` | Postgres + backup |
| `POSTGRES_DB` | No | `esdata` | `runtime deploy` | Postgres + backup |
| `POSTGRES_PORT` | No | `5432` | `runtime deploy` | Publicacion de Postgres |
| `POSTGRES_BIND_ADDRESS` | No | `127.0.0.1` | `runtime deploy` | Bind publicado de Postgres |
| `DATABASE_URL` | Si | | `runtime deploy` | API + workers + crons + ops |
| `APP_ENV` | No | `production` | `runtime deploy` | API |
| `API_BIND_ADDRESS` | No | `127.0.0.1` | `runtime deploy` | Bind publicado de API |
| `API_PORT` | No | `8000` | `runtime deploy` | Puerto publicado de API |
| `WEB_BIND_ADDRESS` | No | `127.0.0.1` | `runtime deploy` | Bind publicado de Web |
| `WEB_PORT` | No | `3000` | `runtime deploy` | Puerto publicado de Web |
| `API_DOMAIN` | Si | | `runtime deploy` | Caddy / TLS API + allowlist Host MCP |
| `WEB_DOMAIN` | Si | | `runtime deploy` | Caddy / TLS Web |
| `CADDY_EMAIL` | No | vacio | `runtime deploy` | Email ACME de Caddy |
| `ESDATA_API_BASE_URL` | Si | | `runtime deploy` | Web SSR -> API |
| `ESDATA_API_KEY` | Si | | `runtime deploy` | API + Web SSR |
| `MCP_API_KEY` | Si | | `runtime deploy` | MCP HTTP privado |

### Workers y fuentes

| Variable | Requerida | Default | Estado | Uso |
|----------|-----------|---------|--------|-----|
| `BOE_API_BASE` | No | `https://www.boe.es/datosabiertos/api/legislacion-consolidada` | `runtime deploy` | Worker BOE + cron |
| `BOE_LEGISLACION_NORMAS` | No | `LIVA,LIRPF,LIS,LGT,ITPAJD,TRLIRNR,LEY10_2010,RDL19_2018,LIVMC,RD_1082_2012,RD_813_2023,IRNR,IIEE,HL,DAC6,DAC6RD,DAC6EU` | `runtime deploy` | Worker BOE + cron |
| `BOE_SYNC_INTERVAL_SECONDS` | No | `3600` | `runtime deploy` | Worker BOE |
| `BDNS_SEED_URLS` | No | vacio | `runtime deploy` | PDFs/documentos BDNS semilla; opcional si `BDNS_STRUCTURED_ENDPOINTS` esta configurado |
| `BDNS_STRUCTURED_ENDPOINTS` | No | `convocatoria,concesion,minimis,ayudas_estado,grandes_beneficiarios,partidos_politicos` | `runtime deploy` | Endpoints oficiales estructurados BDNS a paginar |
| `BDNS_MAX_PAGES` | No | `1` | `runtime deploy` | Paginas maximas por endpoint estructurado BDNS y ejecucion |
| `BDNS_PAGE_SIZE` | No | `100` | `runtime deploy` | Tamano de pagina por endpoint estructurado BDNS |
| `BDNS_SYNC_INTERVAL_SECONDS` | No | `604800` | `runtime deploy` | Worker BDNS |
| `BORME_SEED_URLS` | Si | | `runtime deploy` | Worker BORME + cron |
| `BORME_DISCOVER_FROM_SUMMARY` | No | `true` | `runtime deploy` | Descubrimiento BORME desde sumarios oficiales BOE |
| `BORME_DAYS_BACK` | No | `7` | `runtime deploy` | Dias hacia atras para descubrir sumarios BORME |
| `BORME_MAX_URLS_PER_RUN` | No | `50` | `runtime deploy` | Maximo de PDFs/URLs BORME por ejecucion |
| `BORME_SYNC_INTERVAL_SECONDS` | No | `604800` | `runtime deploy` | Worker BORME |
| `CNMV_SEED_URLS` | Si | | `runtime deploy` | Worker CNMV + cron |
| `CNMV_SYNC_INTERVAL_SECONDS` | No | `604800` | `runtime deploy` | Worker CNMV |
| `SEPBLAC_SEED_URLS` | Si | | `runtime deploy` | Worker SEPBLAC + cron |
| `EU_SANCTIONS_XML_URL` | No | oficial FSF XML | `runtime deploy` | `cron-eu-sanctions-weekly` |
| `SEPBLAC_SYNC_INTERVAL_SECONDS` | No | `604800` | `runtime deploy` | Worker SEPBLAC |
| `CENDOJ_SEED_URLS` | Si | | `runtime deploy` | Worker CENDOJ |
| `CENDOJ_SYNC_INTERVAL_SECONDS` | No | `604800` | `runtime deploy` | Worker CENDOJ |
| `EURLEX_SEED_URLS` | No | vacio | `runtime deploy` | Worker EUR-Lex |
| `EURLEX_SYNC_INTERVAL_SECONDS` | No | `604800` | `runtime deploy` | Worker EUR-Lex |
| `SPARQL_BASE` | No | `https://data.europa.eu/sparql` | `runtime deploy` | Worker EUR-Lex |
| `BDE_SEED_URLS` | No | vacio | `runtime deploy` | Worker BDE + cron; opcional si discovery de circulares esta activo |
| `BDE_DISCOVERY_ENABLED` | No | `true` | `runtime deploy` | Descubrimiento BDE desde listado oficial de circulares |
| `BDE_DISCOVERY_MAX_URLS` | No | `10` | `runtime deploy` | Maximo de URLs BDE descubiertas por ejecucion |
| `BDE_CIRCULARES_URL` | No | `https://www.bde.es/wbe/es/areas-actuacion/normativa/circulares-banco-de-espana/circulares-banco-espana-indice-cronologico/` | `runtime deploy` | Listado oficial de circulares y normativa BdE |
| `BDE_SYNC_INTERVAL_SECONDS` | No | `604800` | `runtime deploy` | Worker BDE |
| `AEPD_SEED_URLS` | No | vacio | `runtime deploy` | Worker AEPD; opcional si discovery AEPD esta activo |
| `AEPD_DISCOVER_FROM_INDEX` | No | `true` | `runtime deploy` | Descubrimiento AEPD desde indice oficial de guias |
| `AEPD_DISCOVER_RESOLUTIONS` | No | `true` | `runtime deploy` | Descubrimiento AEPD desde RSS oficial de resoluciones |
| `AEPD_ENUMERATE_RESOLUTIONS` | No | `false` | `runtime deploy` | Enumeracion acotada de PDFs de resoluciones AEPD por patron oficial |
| `AEPD_GUIDES_INDEX_URL` | No | `https://www.aepd.es/guias-y-herramientas/guias` | `runtime deploy` | Indice oficial de guias AEPD |
| `AEPD_RESOLUTIONS_RSS_URL` | No | `https://www.aepd.es/informes-y-resoluciones/resoluciones/feed.xml` | `runtime deploy` | RSS oficial de resoluciones AEPD |
| `AEPD_MAX_URLS_PER_RUN` | No | `25` | `runtime deploy` | Maximo de URLs AEPD por ejecucion |
| `AEPD_MAX_GUIDE_URLS_PER_RUN` | No | `15` | `runtime deploy` | Maximo de URLs de guias AEPD por ejecucion |
| `AEPD_MAX_RESOLUTION_URLS_PER_RUN` | No | `10` | `runtime deploy` | Maximo de URLs de resoluciones AEPD por ejecucion |
| `AEPD_DISCOVERY_PAGES` | No | `3` | `runtime deploy` | Paginas de indice AEPD a recorrer |
| `AEPD_RESOLUTION_START_YEAR` | No | `2024` | `runtime deploy` | Ano inicial para enumeracion acotada AEPD cuando se habilita |
| `AEPD_RESOLUTION_MAX_PER_TYPE_YEAR` | No | `25` | `runtime deploy` | Limite de candidatos por tipo/ano en enumeracion AEPD |
| `AEPD_RESOLUTION_MAX_CONSECUTIVE_MISSES` | No | `20` | `runtime deploy` | Corte por fallos consecutivos en enumeracion AEPD |
| `AEPD_SYNC_INTERVAL_SECONDS` | No | `604800` | `runtime deploy` | Worker AEPD |
| `DGT_SSL_VERIFY` | No | `false` en `compose.env.example` | `runtime deploy` | Worker DGT + cron |
| `DGT_DISCOVERY` | No | `true` | `runtime deploy` | Worker DGT |
| `DGT_SYNC_INTERVAL_SECONDS` | No | `604800` | `runtime deploy` | Worker DGT |
| `TEAC_SEED_URLS` | Si | | `runtime deploy` | Worker TEAC + cron |
| `TEAC_SYNC_INTERVAL_SECONDS` | No | `604800` | `runtime deploy` | Worker TEAC |
| `MODELOS_SYNC_INTERVAL` | No | `86400` | `runtime deploy` | Worker Modelos |
| `BOE_DIARIO_IDS` | No | vacio | `runtime deploy` | Lista CSV explicita de `BOE-B/S/N` para `cron-boe-diario-daily`; si queda vacia usa discovery por sumario oficial |
| `BOE_DIARIO_DAYS_BACK` | No | `1` | `runtime deploy` | Dias hacia atras para discovery de BOE diario |
| `BOE_DIARIO_MAX_IDS_PER_RUN` | No | `10` | `runtime deploy` | Limite de documentos BOE diario por ejecucion |
| `BOE_DIARIO_FETCH_PDF_FALLBACK` | No | `true` | `runtime deploy` | Permite fallback PDF oficial si el XML diario no trae texto |
| `WORKER_REQUEST_DELAY` | No | `1.0` | `runtime deploy` | Workers BOE/DGT/TEAC/BDNS/BORME/CNMV/SEPBLAC/CENDOJ/EUR-Lex/BDE/AEPD/AEAT |

### Cron y observabilidad

| Variable | Requerida | Default | Estado | Uso |
|----------|-----------|---------|--------|-----|
| `HC_PING_URL_CRON_BOE_DAILY` | No | vacio | `runtime deploy` | `cron-boe-daily` |
| `HC_PING_URL_CRON_BOE_DIARIO_DAILY` | No | vacio | `runtime deploy` | `cron-boe-diario-daily` |
| `HC_PING_URL_CRON_DGT_WEEKLY` | No | vacio | `runtime deploy` | `cron-dgt-weekly` |
| `HC_PING_URL_CRON_TEAC_WEEKLY` | No | vacio | `runtime deploy` | `cron-teac-weekly` |
| `HC_PING_URL_CRON_MODELOS_DAILY` | No | vacio | `runtime deploy` | `cron-modelos-daily` |
| `HC_PING_URL_CRON_AEAT_CURRENT_DAILY` | No | vacio | `runtime deploy` | `cron-aeat-current-daily` |
| `HC_PING_URL_CRON_BDNS_WEEKLY` | No | vacio | `runtime deploy` | `cron-bdns-weekly` |
| `HC_PING_URL_CRON_BORME_WEEKLY` | No | vacio | `runtime deploy` | `cron-borme-weekly` |
| `HC_PING_URL_CRON_CNMV_WEEKLY` | No | vacio | `runtime deploy` | `cron-cnmv-weekly` |
| `HC_PING_URL_CRON_SEPBLAC_WEEKLY` | No | vacio | `runtime deploy` | `cron-sepblac-weekly` |
| `HC_PING_URL_CRON_BDE_WEEKLY` | No | vacio | `runtime deploy` | `cron-bde-weekly` |
| `HC_PING_URL_CRON_EURLEX_MARKET_MONTHLY` | No | vacio | `runtime deploy` | `cron-eurlex-market-monthly` |
| `HC_PING_URL_CRON_ESMA_MIFIR_REPORTING_WEEKLY` | No | vacio | `runtime deploy` | `cron-esma-mifir-reporting-weekly` |
| `HC_PING_URL_CRON_ESMA_FIRDS_DAILY` | No | vacio | `runtime deploy` | `cron-esma-firds-daily` |
| `HC_PING_URL_CRON_ESMA_DLT_WEEKLY` | No | vacio | `runtime deploy` | `cron-esma-dlt-weekly` |
| `HC_PING_URL_OFFICIAL_REGULATORY_REFERENCES` | No | vacio | `runtime deploy` | `cron-official-regulatory-references` |
| `HC_PING_URL_CRON_EU_SANCTIONS_WEEKLY` | No | vacio | `runtime deploy` | `cron-eu-sanctions-weekly` |
| `GRAFANA_ADMIN_PASSWORD` | No | vacio | `runtime deploy` | Perfil `prod` de Grafana |
| `GRAFANA_ROOT_URL` | No | `https://tudominio.com/grafana/` | `runtime deploy` | Perfil `prod` de Grafana |

Notas operativas de `runtime deploy`:

- En `5.3`, `cron`, `backup`, `ops` y observabilidad siguen contando como parte del boundary `runtime deploy`, aunque algunos servicios se levanten por profile o scheduler externo.
- `DGT_SSL_VERIFY` tiene fallback distinto en `worker-dgt` (`true`) y `cron-dgt-weekly` (`false`) dentro de Compose; el template activo fija un valor explicito para evitar ambiguedad operativa.

## Variables `code-only`

| Variable | Default | Estado | Uso | Referencia principal |
|----------|---------|--------|-----|----------------------|
| `DATABASE_PUBLIC_URL` | vacio | `code-only` | Scripts manuales que aceptan URL publica como alternativa a `DATABASE_URL` | `scripts/seed-modelos.py`, `scripts/seed-modelos-v2.py`, `scripts/maintenance/validate-cron-run.py` |
| `ESDATA_CORS_ORIGINS` | `http://localhost:3000,http://localhost:8000` | `code-only` | CORS del API | `apps/api/main.py` |
| `ESDATA_RATE_LIMIT_ENABLED` | `true` | `code-only` | Rate limiting general del API | `apps/api/middleware/rate_limit.py` |
| `ESDATA_HSTS_ENABLED` | `false` | `code-only` | Cabecera HSTS | `apps/api/middleware/security_headers.py` |
| `ESDATA_SENTRY_DSN` | vacio | `code-only` | Sentry opcional en workers | `apps/workers/runtime.py` |
| `MCP_RATE_LIMIT_PER_MINUTE` | `60` | `code-only` | Rate limiting especifico del endpoint MCP | `apps/api/mcp_security.py` |
| `AGENT_MONITOR_ENABLED` | `false` | `code-only` | Activacion opt-in del monitor de agentes | `apps/api/agent_monitor.py` |
| `AGENT_MONITOR_INTERVAL` | `300` | `code-only` | Intervalo del monitor de agentes | `apps/api/agent_monitor.py` |
| `AGENT_MONITOR_ENTIDAD` | `sociedad_valores` | `code-only` | Entidad base del monitor | `apps/api/agent_monitor.py` |
| `AGENT_MONITOR_PRIORIDAD` | `media` | `code-only` | Prioridad base del monitor | `apps/api/agent_monitor.py` |
| `LOG_LEVEL` | `INFO` | `code-only` | Logging compartido | `libs/python/esdata_common/logging.py` |
| `LOG_FORMAT` | `text` | `code-only` | Logging compartido | `libs/python/esdata_common/logging.py` |
| `SYNC_INTERVAL_SECONDS` | depende del worker | `code-only` | Override generico usado por workers en CLI/manual; el deploy activo lo deriva desde `*_SYNC_INTERVAL_SECONDS` | `apps/workers/*.py` |
| `BOE_ONLY_BLOCK_IDS` | vacio | `code-only` | Filtro manual/debug para BOE | `apps/workers/boe.py` |
| `DB_POOL_SIZE` | `10` en `apps/api/db.py`, `5` en `esdata_common.db` | `code-only` | Tamano de pool SQLAlchemy | `apps/api/db.py`, `libs/python/esdata_common/db.py` |
| `DB_MAX_OVERFLOW` | `20` | `code-only` | Overflow del pool usado por `apps/api/db.py` | `apps/api/db.py` |
| `DB_POOL_MAX_OVERFLOW` | `10` | `code-only` | Overflow del pool usado por `libs/python/esdata_common/db.py` | `libs/python/esdata_common/db.py` |
| `DB_POOL_RECYCLE` | `1800` | `code-only` | Reciclado del pool compartido | `libs/python/esdata_common/db.py` |

## Variables `legacy/no cableada`

| Variable | Estado | Nota |
|----------|--------|------|
| `MCP_SECRET_ACTIVE` | `legacy/no cableada` | Sigue apareciendo en docs antiguos/perimetrales, pero el deploy Compose activo no la cablea |
| `MCP_SECRET_PREVIOUS` | `legacy/no cableada` | Igual que `MCP_SECRET_ACTIVE`; fuera del boundary activo de Compose |
| `CLOUDFLARE_ZONE_ID` | `legacy/no cableada` | Variable historica de workflows/docs de perimetro; no forma parte del deploy Compose activo |
| `CLOUDFLARE_API_TOKEN` | `legacy/no cableada` | Igual que `CLOUDFLARE_ZONE_ID`; no cableada hoy al runtime activo |
| `PGHOST` | `legacy/no cableada` | Documentada historicamente como alternativa a `DATABASE_URL`, pero la configuracion actual no la resuelve |
| `PGPORT` | `legacy/no cableada` | Igual que `PGHOST`; solo queda como convencion externa de tooling |
| `PGUSER` | `legacy/no cableada` | Igual que `PGHOST`; no la carga la app actual |
| `PGPASSWORD` | `legacy/no cableada` | Igual que `PGHOST`; puede usarse en tooling externo, pero no en el runtime del repo |
| `PGDATABASE` | `legacy/no cableada` | Igual que `PGHOST`; no la resuelve la app actual |
| `REDIS_URL` | `legacy/no cableada` | Sin referencias activas en el codigo actual |
| `SECRET_KEY` | `legacy/no cableada` | Sin referencias activas en el codigo actual |
| `SLACK_WEBHOOK_URL` | `legacy/no cableada` | Sin referencias activas en el codigo actual |

## Verificacion minima del deploy activo

Usar siempre el template activo del deploy para validar el boundary:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml config
```

Para preparar `/etc/esdata/esdata.env`, partir de:

```bash
sudo mkdir -p /etc/esdata
sudo cp infra/deploy/compose.env.example /etc/esdata/esdata.env
sudo chmod 600 /etc/esdata/esdata.env
```

## Referencias

- `infra/deploy/docker-compose.prod.yml` - boundary del runtime Compose activo
- `infra/deploy/compose.env.example` - plantilla del deploy activo
- `.env.example` - inventario amplio para runtime, tooling local y codigo no cableado al deploy activo
- `apps/web/.env.example` - ejemplo minimo del frontend aislado
- `apps/api/db.py` - `DATABASE_URL`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`
- `libs/python/esdata_common/db.py` - `DB_POOL_SIZE`, `DB_POOL_MAX_OVERFLOW`, `DB_POOL_RECYCLE`
- `libs/python/esdata_common/config.py` - resolucion base de env vars
- `apps/api/mcp_security.py` - `MCP_RATE_LIMIT_PER_MINUTE`
- `apps/api/agent_monitor.py` - `AGENT_MONITOR_*`
- `apps/workers/boe.py` - `BOE_ONLY_BLOCK_IDS`

# Operacion tecnica

## Despliegue de referencia

El despliegue de referencia del proyecto es `Docker Compose`.

Las referencias a `Railway` son solo historicas y no forman parte de la operacion actual.

La topologia de referencia actual incluye:

- `caddy`
- `postgres`
- `api`
- `web`
- multiples `worker-*`

## Documentacion tecnica relacionada

- `../deployment/overview.md`
- `../deployment/server-installation.md`
- `../deployment/rollback.md`
- `../environment-variables.md`
- `../database.md`
- `../operations/README.md`

## Que debe conocer un operador

- variables de entorno requeridas
- forma de levantar servicios
- forma de verificar salud basica
- como consultar la documentacion operativa y runbooks

## Comandos operativos minimos

Levantar stack principal:

```bash
docker compose -f infra/deploy/docker-compose.prod.yml up -d
```

Ver estado:

```bash
docker compose -f infra/deploy/docker-compose.prod.yml ps
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/status
```

Aplicar migraciones:

```bash
docker compose -f infra/deploy/docker-compose.prod.yml exec api alembic upgrade head
```

Ejecutar un worker una vez:

```bash
docker compose -f infra/deploy/docker-compose.prod.yml run --rm worker-boe python boe.py --run-once
```

## Variables clave

El detalle completo esta en `../environment-variables.md`, pero operativamente destacan:

- `DATABASE_URL`
- `POSTGRES_PASSWORD`
- `API_DOMAIN`
- `WEB_DOMAIN`
- `ESDATA_API_BASE_URL`
- `ESDATA_API_KEY`
- `MCP_API_KEY`
- semillas por worker como `TEAC_SEED_URLS`, `CNMV_SEED_URLS`, `SEPBLAC_SEED_URLS`, `CENDOJ_SEED_URLS`, `EURLEX_SEED_URLS`, `BDE_SEED_URLS` y `AEPD_SEED_URLS`

## Seguridad y exposicion

La API incorpora hoy varias capas operativas segun el codigo:

- rate limiting middleware general
- guard especifico para `/mcp`
- headers de seguridad
- CORS configurable por `ESDATA_CORS_ORIGINS`
- autenticacion obligatoria por API key en runtime normal via `ESDATA_API_KEY`
- autenticacion obligatoria de `/mcp` via `MCP_API_KEY`
- endpoint `/metrics` si Prometheus esta disponible

Reglas operativas actuales:

- fuera de `APP_ENV=test`, la API no debe arrancar sin `ESDATA_API_KEY`
- fuera de `APP_ENV=test`, `/mcp` no debe quedar operativo sin `MCP_API_KEY`
- `/metrics` no debe tratarse como superficie publica por defecto

## Salud y observabilidad

Endpoints y senales relevantes:

- `/health` devuelve estado de la API y conectividad DB
- `/status` agrega estado de workers y freshness
- cada worker debe dejar en `sync_log` al menos `rows_processed`, `errors` y `duration_ms`; si faltan, la observabilidad se considera parcial aunque el endpoint responda
- `/metrics` se monta si el soporte esta disponible
- Sentry es opcional via `ESDATA_SENTRY_DSN`

Comprobacion operativa minima recomendada:

```bash
curl -s http://127.0.0.1:8000/status
```

Senales que deben vigilarse:

- `stale=true` en workers que deberian haber corrido dentro de su cadencia
- `status=error` o `errors > 0`
- `rows_processed` en cero de forma recurrente cuando la fuente deberia moverse

## Regla de documentacion tecnica incremental

Si una tarea cambia setup local, despliegue, variables de entorno, dependencias operativas, rutas de acceso, endpoints de salud o runbooks, este capitulo o la documentacion tecnica enlazada debe actualizarse antes de cerrar la tarea.

Referencias utiles:

- `../deployment/overview.md`
- `../operations/README.md`
- `../operations/runbooks/backup-restore.md`

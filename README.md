# esdata

Infraestructura de datos y consulta fiscal-regulatoria con trazabilidad a fuente oficial.

`esdata` combina:

- `API` FastAPI para consultas estructuradas
- `MCP` para clientes compatibles con agentes y LLMs
- workers de ingestion por fuente
- PostgreSQL como capa de persistencia
- UI web interna para consulta y paneles operativos

## Estado actual

- Despliegue de referencia: `Docker Compose`
- cualquier referencia a plataformas antiguas es solo historica y no tiene valor operativo actual
- Foco funcional actual: consulta fiscal-regulatoria y capas de compliance con perfil prioritario `sociedad de valores` en Espana
- Fuente activa de estado, fases y siguiente paso: `docs/master-execution-roadmap.md`

## Que incluye hoy

Dominios y capas ya presentes en el repo:

- legislacion consolidada
- doctrina administrativa
- modelos AEAT
- obligaciones regulatorias
- cambios regulatorios
- workflow de compliance
- empresas y entidades
- screening
- PGC
- fuentes documentales como `BDNS`, `BORME`, `CNMV`, `SEPBLAC`, `CENDOJ`, `EUR-Lex`, `BDE` y `AEPD`

## Superficies principales

- `API`: `apps/api`
- `MCP`: montado sobre la API y catalogo compartido en `apps/api/mcp_catalog.py`
- `Web`: `apps/web`
- `Workers`: `apps/workers`

Rutas API especialmente utiles:

- `GET /health`
- `GET /status`
- `GET /v1/buscar`
- `GET /v1/legislacion/...`
- `GET /v1/doctrina/...`
- `GET /v1/modelos/...`
- `GET /v1/obligaciones/...`
- `GET /v1/compliance/workflow`
- `GET /v1/cambios`
- `GET /v1/entidades/...`
- `POST /v1/screening/`
- `GET /v1/pgc/...`
- `GET /mcp`

## Estructura del repo

- `apps/api` — API FastAPI, routers, schemas y capa MCP
- `apps/web` — UI web interna con pantallas de consulta y admin
- `apps/workers` — ingestion y sincronizacion por fuente
- `scripts/` — tooling manual, evaluacion, ops, seeds y mantenimiento
- `alembic/versions` — migraciones de base de datos
- `infra/deploy` — despliegue Docker Compose y Caddy
- `docs/` — documentacion viva, roadmap, manual y archivo historico

## Arranque rapido

Levantar stack principal:

```bash
docker compose -f infra/deploy/docker-compose.prod.yml up -d
```

Aplicar migraciones:

```bash
docker compose -f infra/deploy/docker-compose.prod.yml exec api alembic upgrade head
```

Verificar salud:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/status
```

Ejemplos funcionales:

```bash
curl -G -s http://127.0.0.1:8000/v1/buscar --data-urlencode "q=iva intracomunitario"
curl -s http://127.0.0.1:8000/v1/modelos/303
curl -G -s http://127.0.0.1:8000/v1/obligaciones/aplicables --data-urlencode "tipo_entidad=sociedad_valores"
```

## Desarrollo local

API:

```bash
pytest apps/api/tests/test_smoke.py -q
```

Workers:

```bash
pytest apps/workers/tests/test_boe.py -q
pytest apps/workers/tests/test_dgt.py -q
pytest apps/workers/tests/test_teac.py -q
pytest apps/workers/tests/test_modelos.py -q
```

Web:

```bash
npm --prefix apps/web install
npm --prefix apps/web run dev
npm --prefix apps/web run test
npm --prefix apps/web run build
```

OpenAPI reducida para integraciones:

```bash
python scripts/ops/export-gpt-openapi.py --output docs/openapi-gpt.json
python scripts/ops/export-gpt-openapi.py --openapi 3.0.3 --output docs/openapi-gpt-3.0.json
```

## Documentacion recomendada

Leer en este orden:

1. `docs/master-execution-roadmap.md`
2. `docs/manual-usuario/README.md`
3. `docs/README.md`
4. `docs/deployment/overview.md`
5. `docs/operations/README.md`
6. `docs/environment-variables.md`

## Reglas estructurales

- la raiz del repo debe mantenerse limpia; artefactos locales van a `logs/`, `tmp/` o fuera del repo
- `apps/*` contiene codigo de producto, no scripts manuales
- `scripts/` contiene tooling y tareas operativas no-runtime
- `docs/archive/` contiene historicos y no debe competir con la documentacion activa

## Reglas importantes

- `Railway` no se usa y no debe proponerse como alternativa operativa
- no tratar el `README` como fuente de estado vivo del proyecto
- para uso humano y funcional, usar el manual en `docs/manual-usuario/`
- para fase activa y siguiente paso, usar `docs/master-execution-roadmap.md`

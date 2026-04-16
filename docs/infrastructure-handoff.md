# Handoff a infraestructura

## Objetivo

Este documento resume lo que un equipo de infraestructura necesita para desplegar, operar y verificar `esdata` fuera del contexto original de Railway.

## Resumen ejecutivo

`esdata` es un sistema compuesto por:

- 1 API publica FastAPI
- 1 frontend Next.js
- 4 workers de ingesta continua
- 4 procesos programados tipo cron
- 1 base de datos PostgreSQL
- 1 capa opcional perimetral Cloudflare para cache, rate limiting y proteccion de `/mcp`

El sistema puede ejecutarse en un servidor empresarial basado en contenedores. La forma mas natural de primer aterrizaje fuera de Railway es Docker Compose productivo o una plataforma interna que ejecute contenedores equivalentes.

Artefactos ya preparados en el repo:

- `infra/deploy/docker-compose.prod.yml`
- `infra/deploy/compose.env.example`
- `docs/operations/runbooks/deploy-compose.md`
- `docs/infrastructure-acceptance-checklist.md`

## Servicios a desplegar

### Core

#### API

- nombre actual: `esdata`
- raiz actual: `apps/api`
- comando actual: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- puerto HTTP: `8000` interno en contenedor
- healthcheck: `/health`

#### Web

- nombre actual: `web`
- raiz actual: `apps/web`
- comando actual: `npm run build && npm start`
- puerto HTTP: el de Next.js configurado por runtime
- healthcheck: `/`

#### Base de datos

- tipo: PostgreSQL
- uso: almacenamiento principal de legislacion, doctrina, modelos y trazas de workers

### Workers continuos

#### `worker-boe`

- raiz actual: `apps/workers`
- comando actual: `python boe.py`
- funcion: sincronizacion continua de legislacion BOE

#### `worker-dgt`

- raiz actual: `apps/workers`
- comando actual: `python dgt.py`
- funcion: sincronizacion continua de doctrina DGT

#### `worker-teac`

- raiz actual: `apps/workers`
- comando actual: `python teac.py`
- funcion: sincronizacion continua de resoluciones TEAC

#### `worker-modelos`

- raiz actual: `apps/workers`
- comando actual: `python modelos.py`
- funcion: sincronizacion continua de modelos AEAT

### Cron jobs

#### `cron-boe-daily`

- comando actual: `python boe.py --run-once`
- schedule actual: `0 6 * * *`

#### `cron-dgt-weekly`

- comando actual: `python dgt.py --run-once`
- schedule actual: `0 7 * * 1`

#### `cron-teac-weekly`

- comando actual: `python teac.py --run-once`
- schedule actual: `0 8 * * 1`

#### `cron-modelos-daily`

- comando actual: `python modelos.py --run-once`
- schedule actual: `0 5 * * *`

## Dependencias externas

El sistema depende de conectividad saliente hacia:

- `www.boe.es`
- `petete.tributos.hacienda.gob.es`
- `sede.agenciatributaria.gob.es`
- destinos TEAC definidos en `TEAC_SEED_URLS`
- opcionalmente `api.cloudflare.com`

## Variables de entorno minimas

### Imprescindibles

- API: `DATABASE_URL`
- Web: `ESDATA_API_BASE_URL`
- worker BOE: `DATABASE_URL`
- worker DGT: `DATABASE_URL`
- worker TEAC: `DATABASE_URL`, `TEAC_SEED_URLS`
- worker Modelos: `DATABASE_URL`

### Recomendadas

- `BOE_API_BASE`
- `BOE_LEGISLACION_NORMAS`
- `SYNC_INTERVAL_SECONDS`
- `MODELOS_SYNC_INTERVAL`
- `DGT_SSL_VERIFY`

### Perimetro opcional

- `MCP_SECRET_ACTIVE`
- `MCP_SECRET_PREVIOUS`
- `CLOUDFLARE_ZONE_ID`
- `CLOUDFLARE_API_TOKEN`

## Bootstrap de base de datos

El repo ya incorpora Alembic como capa formal para evolucion futura de schema y mantiene el SQL historico como compatibilidad heredada.

Ruta recomendada:

1. `make db-upgrade`

Ruta heredada:

1. `make bootstrap-db`

Orden actual recomendado:

1. `infra/sql/init.sql`
2. `infra/sql/002_fulltext_search.sql`
3. `infra/sql/003_modelos_aeat.sql`
4. `infra/sql/004_modelos_v2.sql`
5. `infra/sql/004_norma_classification.sql`
6. `infra/sql/docker-init.sql` solo para entorno docker/local segun necesidad

Seeds relevantes:

1. `python scripts/seed-modelos.py --db-url ...`
2. `python scripts/seed-modelos-v2.py --db-url ... --campana 2025`

Validaciones manuales ya existentes:

- `verify_railway.py`
- `scripts/validate-cron-run.py`
- `scripts/smoke-check.py`

## Orden recomendado de arranque

1. levantar PostgreSQL
2. aplicar schema y seeds necesarios
3. arrancar API
4. verificar `/health` y `/status`
5. arrancar workers continuos
6. arrancar frontend web
7. habilitar cron jobs externos o contenedores programados
8. activar perimetro Cloudflare si aplica

## Criterios de aceptacion operativa

El sistema debe considerarse correctamente desplegado cuando se cumpla esto:

- `GET /health` responde `200`
- `GET /status` responde `200`
- `GET /openapi.json` responde `200`
- `GET /v1/legislacion/cobertura` devuelve normas
- `GET /v1/modelos` devuelve modelos
- `GET /` del frontend responde correctamente
- existe conectividad desde workers hacia sus fuentes externas
- los workers registran ejecuciones en `sync_log`

## Observabilidad actual

### Disponible hoy

- `/health`
- `/status`
- tabla `sync_log`
- `docs/operations/README.md`
- logs stdout/stderr de contenedores
- smoke tests de deploy en GitHub Actions
- `verify_railway.py`

### Limitaciones actuales

- no hay metricas Prometheus ni equivalente
- no hay alertado integrado en runtime
- el formato de logs no esta unificado entre todos los procesos

## Riesgos operativos actuales

### 1. Migraciones manuales

- no existe Alembic ni versionado formal aplicado en BD
- requiere disciplina documental y control de ejecucion

### 2. Configuracion no totalmente normalizada

- hay variables documentadas que no consume el runtime
- hay scripts que usan variables auxiliares no centrales

### 3. Reutilizacion tecnica limitada

- API y workers no comparten una libreria comun formal
- parte del conocimiento sigue embebido en scripts y docs de sesion

### 4. Dependencia de fuentes externas HTML

- DGT, TEAC y AEAT dependen de scraping y parsing HTML
- cambios en markup externo pueden romper sincronizaciones

## Runbook minimo para infraestructura

### Comprobacion inicial

1. verificar variables de entorno por servicio
2. verificar resolucion DNS y salida HTTPS a fuentes externas
3. verificar acceso a PostgreSQL
4. comprobar salud de API y web
5. comprobar que `sync_log` recibe nuevas entradas

### Recuperacion basica

1. revisar logs del servicio afectado
2. comprobar variables de entorno especificas del worker
3. validar conectividad a la fuente externa correspondiente
4. ejecutar el worker en modo `--run-once` para aislar fallo
5. revisar impacto en `sync_log`

### Validacion post-deploy

1. ejecutar checks HTTP equivalentes a los de `.github/workflows/deploy.yml`
2. validar estado de trabajadores
3. validar que el frontend resuelve contra la API correcta
4. ejecutar scripts de validacion doctrinal si hubo cambios de datos

## Requisitos recomendados para el futuro entorno empresarial

### Minimos

- contenedores o runtime equivalente
- PostgreSQL gestionado o autocontenido con backups
- scheduler para jobs periodicos
- gestion de secretos separada del repo
- logs centralizados

### Recomendados

- reverse proxy corporativo
- monitorizacion y alertas
- backups automatizados de PostgreSQL
- entorno staging separado de produccion
- despliegues con rollback controlado

## Gaps a cerrar antes de un handoff definitivo

1. documentar arquitectura y variables como contrato estable
2. normalizar configuracion Python compartida
3. decidir estrategia formal de migraciones
4. preparar despliegue portable fuera de Railway
5. completar runbooks y observabilidad minima

## Estado del handoff

Con la estructura actual, el proyecto ya es transferible a un equipo tecnico con experiencia, pero todavia no esta en su punto ideal de madurez operativa. El principal riesgo del handoff hoy no es la falta de contenedores, sino la falta de normalizacion completa en configuracion, migraciones y operacion.

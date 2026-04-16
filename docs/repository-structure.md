# Estructura del repositorio

## Objetivo

Este documento describe la estructura real actual del repo y el papel de cada carpeta para facilitar el mantenimiento y el handoff a infraestructura.

## Raiz del repositorio

Archivos principales:

- `README.md`: vista general del proyecto, cobertura y rutas publicas
- `STRUCTURE.md`: snapshot descriptivo de la estructura funcional del repo
- `DEPLOY_CHECKLIST.md`: checklist manual de despliegue y verificacion
- `Makefile`: comandos raiz de test, lint, bootstrap y ejecucion local
- `docker-compose.yml`: entorno local y de desarrollo integrado
- `railway.toml`: definicion actual de servicios y crons en Railway
- `.env.example`: ejemplo de variables de entorno
- `env.example`: copia historica del ejemplo de entorno
- `verify_railway.py`: comprobacion por CLI del despliegue en Railway
- `pre_commit_check.py`: script auxiliar local
- `esdata_prd_v1.md`: PRD tecnico y funcional base

## Directorios principales

### `apps/`

Contiene las aplicaciones desplegables del sistema.

#### `apps/api/`

Backend FastAPI.

Archivos clave:

- `main.py`: inicializa la app y monta routers
- `db.py`: engine y sesion SQLAlchemy
- `mcp_server.py`: monta la superficie MCP sobre FastAPI
- `schemas.py`: modelos Pydantic de respuesta
- `requirements.txt`: dependencias Python de la API

Subdirectorios:

- `routers/`: endpoints HTTP por dominio funcional
- `services/`: logica auxiliar, hoy centrada en busqueda
- `tests/`: pruebas de API

#### `apps/workers/`

Workers Python de ingesta y sincronizacion.

Archivos clave:

- `boe.py`: ingesta de legislacion BOE y asegurado basico de esquema
- `dgt.py`: ingesta de doctrina DGT desde Petete
- `teac.py`: ingesta de resoluciones TEAC desde URLs semilla
- `modelos.py`: scraping de modelos AEAT y campanas
- `requirements.txt`: dependencias Python de workers
- `Dockerfile`: imagen generica para workers

Subdirectorios:

- `tests/`: pruebas de workers y fixtures

#### `apps/web/`

Frontend publico en Next.js.

Archivos clave:

- `package.json`: scripts y dependencias del frontend
- `next.config.ts`: configuracion Next.js
- `tailwind.config.ts`: configuracion Tailwind
- `Dockerfile`: build y runtime del frontend

Subdirectorios:

- `app/`: rutas App Router
- `components/`: componentes reutilizables
- `lib/`: cliente API, labels, tipos y tests

### `docs/`

Documentacion tecnica y operativa del proyecto.

Contenido actual relevante:

- `deploy-commands.md`
- `operations/README.md`
- `production-status-*.md`
- `session-status-*.md`
- `postmortem-sprint-2.md`
- `openapi-gpt.json`
- `openapi-gpt-3.0.json`
- `professionalization-roadmap.md`

Subdirectorios:

- `superpowers/plans/`
- `superpowers/specs/`

Observacion:

`docs/` contiene hoy mezcla de documentacion viva, snapshots de sesiones y artefactos operativos. A medio plazo conviene separar:

- documentacion permanente
- documentacion de despliegue
- bitacoras/snapshots de sesiones

### `infra/`

Infraestructura y soporte de despliegue.

Subdirectorios:

- `sql/`: esquema, migraciones manuales y bootstrap de base de datos
- `cloudflare/`: worker perimetral para cache, rate limiting y proteccion de `/mcp`

### `scripts/`

Scripts operativos y de soporte.

Contenido actual:

- `seed-modelos.py`
- `seed-modelos-v2.py`
- `export-gpt-openapi.py`
- `validate-cron-run.py`
- `test_validate_cron_run.py`

Responsabilidades:

- poblar datos base
- exportar OpenAPI reducida para ChatGPT Actions
- validar ejecuciones de cron y calidad de enlaces doctrinales

## Dependencias entre directorios

### API

- depende de PostgreSQL
- depende del schema definido en `infra/sql`
- no depende directamente del frontend

### Workers

- dependen de PostgreSQL
- dependen de fuentes externas oficiales
- comparten tablas con la API
- reutilizan logica comun de facto, pero sin libreria compartida formal

### Web

- depende solo de la API publica
- usa `ESDATA_API_BASE_URL`

### Scripts

- dependen de acceso a base de datos y del schema real
- algunos asumen variables `DATABASE_URL` o `DATABASE_PUBLIC_URL`

## Zonas con mas deuda estructural

### 1. Falta de libreria comun Python

No existe hoy una carpeta equivalente a `libs/python/esdata_common` para compartir:

- configuracion
- logging
- helpers de DB
- clientes HTTP comunes

### 2. Mezcla de documentacion permanente y transitoria

`docs/` mezcla artefactos que deberian vivir en categorias distintas.

### 3. Doble ejemplo de entorno

Coexisten `.env.example` y `env.example`. Esto puede generar confusion durante un handoff.

## Recomendacion de evolucion

Sin romper la estructura actual, la evolucion recomendada es:

1. mantener `apps/` como capa de entrypoints desplegables
2. introducir una libreria comun Python fuera de `apps/`
3. reorganizar `docs/` en documentacion permanente y operativa
4. mover artefactos de despliegue portable a `infra/deploy/`
5. anadir una capa raiz de automatizacion con `Makefile` o scripts equivalentes

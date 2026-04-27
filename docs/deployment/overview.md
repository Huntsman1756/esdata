# Despliegue — Overview

## Resumen

El despliegue activo de `esdata` es Docker Compose.

No hay plataforma PaaS activa. Toda referencia a plataformas anteriores pertenece solo al archivo historico en `docs/archive/`.

## Superficies desplegadas

- `api` — backend FastAPI
- `web` — UI interna
- `postgres` — persistencia principal
- `caddy` — reverse proxy y TLS
- `worker-*` — ingestion y pipelines por fuente
- `ops` — tareas operativas puntuales cuando el perfil correspondiente este habilitado

## Principio operativo

El runtime del producto se despliega desde `apps/*`.

El tooling no-runtime no se despliega como servicio principal:

- seeds
- backfills
- verificaciones manuales
- wrappers locales
- scripts de diagnostico

Todo eso vive en `scripts/`.

## Docker Compose

Archivo de referencia:

- `infra/deploy/docker-compose.prod.yml`

Perfiles operativos:

- default — runtime principal
- `cron` — ejecucion manual/oneshot de jobs
- `ops` — migraciones, backups y checks administrativos

## Flujo de despliegue recomendado

1. preparar servidor
2. copiar repo y variables de entorno
3. levantar stack
4. aplicar migraciones
5. verificar salud
6. ejecutar tareas operativas puntuales si hacen falta

## Verificacion minima post-deploy

- `docker compose -f infra/deploy/docker-compose.prod.yml ps`
- `curl -s http://127.0.0.1:8000/health`
- `curl -s http://127.0.0.1:8000/status`
- verificacion de migraciones y esquema si hubo cambios de DB

## Boundaries importantes

- no desplegar scripts manuales como si fueran runtime permanente
- no asumir que `apps/api` contiene tooling operativo
- no introducir secretos en imagenes o archivos versionados
- no usar docs historicas como guia de despliegue activa

## Documentacion relacionada

- `docs/architecture.md`
- `docs/operations/README.md`
- `docs/deployment/server-installation.md`
- `docs/deployment/rollback.md`
- `infra/AGENTS.md`

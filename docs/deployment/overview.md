# Deployment Overview

## Estado actual

El despliegue de referencia hoy es Docker Compose, con configuracion viva en
`infra/deploy/docker-compose.prod.yml` y variables en `infra/deploy/compose.env.example`.

## Objetivo operativo

Mantener un despliegue portable y reproducible para servidor empresarial,
con scheduler externo para crons y secretos gestionados fuera del repo.

## Componentes desplegables

- API FastAPI
- Web Next.js
- Workers continuos
- Cron jobs
- PostgreSQL
- Cloudflare opcional para cache y proteccion MCP

## Recomendacion

Primer aterrizaje empresarial recomendado:

1. contenedores por servicio
2. PostgreSQL separado
3. scheduler externo para crons
4. proxy inverso corporativo
5. secretos gestionados fuera del repo

## Artefactos disponibles en el repo

- `infra/deploy/docker-compose.prod.yml`
- `infra/deploy/Caddyfile`
- `infra/deploy/Dockerfile.ops`
- `infra/deploy/systemd/*`
- `infra/deploy/compose.env.example`
- `docs/operations/OPERATIONS.md`
- `docs/operations/runbooks/deploy-compose.md`
- `alembic.ini`

## Regla de interpretacion

Los documentos o scripts de Railway solo cuentan como historicos. El flujo activo de despliegue es Compose + `ops` + scheduler externo para `cron-*`.

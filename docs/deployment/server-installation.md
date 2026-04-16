# Instalación en servidor

## Objetivo

Referencia minima para levantar `esdata` en un servidor empresarial con contenedores.

## Pasos

1. preparar PostgreSQL
2. aplicar bootstrap de schema con Alembic o, de forma heredada, con SQL manual
3. cargar variables de entorno por servicio
4. desplegar API
5. desplegar workers continuos
6. desplegar frontend
7. configurar cron jobs
8. validar salud y rutas publicas

## Atajo con Compose

Si se usa Docker Compose como primer despliegue empresarial, tomar como base:

- `infra/deploy/docker-compose.prod.yml`
- `infra/deploy/compose.env.example`
- `docs/operations/runbooks/deploy-compose.md`

## Migraciones recomendadas

Preferencia actual:

1. `make db-upgrade`

Compatibilidad heredada:

1. `make bootstrap-db`

## Validaciones minimas

- `/health`
- `/status`
- `/v1/legislacion/cobertura`
- `/v1/modelos`
- frontend accesible

## Requisitos minimos

- salida HTTPS a BOE, DGT, AEAT y TEAC
- almacenamiento persistente para PostgreSQL
- logs accesibles por servicio

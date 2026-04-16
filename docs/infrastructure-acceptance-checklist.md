# Checklist de aceptación de infraestructura

## Objetivo

Checklist final para validar que `esdata` queda aceptado por el equipo de infraestructura en un entorno empresarial.

## Infraestructura base

- [ ] PostgreSQL desplegado con persistencia
- [ ] backups de PostgreSQL definidos
- [ ] conectividad saliente a BOE, DGT, AEAT y TEAC validada
- [ ] secretos gestionados fuera del repo
- [ ] logs accesibles por servicio
- [ ] scheduler definido para cron jobs

## Despliegue

- [ ] API desplegada y accesible
- [ ] Web desplegada y accesible
- [ ] `worker-boe` desplegado
- [ ] `worker-dgt` desplegado
- [ ] `worker-teac` desplegado
- [ ] `worker-modelos` desplegado
- [ ] cron jobs definidos o sustituidos por scheduler corporativo

## Configuración

- [ ] variables mínimas por servicio cargadas
- [ ] `DATABASE_URL` validada
- [ ] `ESDATA_API_BASE_URL` validada
- [ ] `TEAC_SEED_URLS` validada
- [ ] `DGT_SSL_VERIFY` validada según política del entorno

## Base de datos

- [ ] `make db-upgrade` aplicado o estrategia equivalente aprobada
- [ ] seeds de modelos ejecutadas si aplica
- [ ] tablas críticas accesibles
- [ ] `sync_log` operativo

## Validación funcional

- [ ] `GET /health` responde `200`
- [ ] `GET /status` responde `200`
- [ ] `GET /openapi.json` responde `200`
- [ ] `GET /v1/legislacion/cobertura` devuelve datos
- [ ] `GET /v1/modelos` devuelve datos
- [ ] frontend carga correctamente
- [ ] `scripts/smoke-check.py --base-url ...` pasa

## Operación

- [ ] runbooks revisados por infraestructura
- [ ] procedimiento de rollback revisado
- [ ] procedimiento de redeploy revisado
- [ ] procedimiento de validación post-deploy revisado

## Cierre

- [ ] infraestructura puede arrancar el sistema sin ayuda del autor original
- [ ] infraestructura puede validar el sistema sin leer el código
- [ ] infraestructura puede reiniciar y recuperar workers con los runbooks disponibles

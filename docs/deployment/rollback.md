# Rollback

## Resumen

Este documento describe los procedimientos de rollback para cada escenario posible.

## Rollback de aplicacion (sin cambios de schema)

Cuando la nueva version de codigo no introduce cambios de base de datos.

```bash
# 1. Parar servicios afectados
docker compose -f infra/deploy/docker-compose.prod.yml down api web

# 2. Desplegar version anterior
git checkout <tag_o_commit_anterior>
docker compose -f infra/deploy/docker-compose.prod.yml build api web
docker compose -f infra/deploy/docker-compose.prod.yml up -d api web

# 3. Verificar
curl -s https://api.tudominio.com/health
```

## Rollback de schema (con cambios de schema)

Cuando la nueva version introduce cambios de schema que no se pueden revertir automaticamente.

### Escenario A: Migracion reversible

```bash
# 1. Revertir migracion
docker compose -f infra/deploy/docker-compose.prod.yml exec api alembic downgrade -1

# 2. Revertir aplicacion
git checkout <tag_anterior>
docker compose -f infra/deploy/docker-compose.prod.yml build api
docker compose -f infra/deploy/docker-compose.prod.yml down api
docker compose -f infra/deploy/docker-compose.prod.yml up -d api

# 3. Verificar
docker compose -f infra/deploy/docker-compose.prod.yml exec api alembic current
```

### Escenario B: Migracion irreversible

```bash
# 1. Restaurar backup de base de datos
#    (buscar backup anterior al deploy fallido)
gunzip -c /backups/esdata_20260425_030000.sql.gz | \
  docker compose -f infra/deploy/docker-compose.prod.yml exec -T postgres psql -U esdata esdata

# 2. Revertir aplicacion
git checkout <tag_anterior>
docker compose -f infra/deploy/docker-compose.prod.yml build api
docker compose -f infra/deploy/docker-compose.prod.yml down api
docker compose -f infra/deploy/docker-compose.prod.yml up -d api

# 3. Verificar integridad
docker compose -f infra/deploy/docker-compose.prod.yml exec postgres psql -U esdata -d esdata -c \
  "SELECT COUNT(*) FROM version_articulo; SELECT COUNT(*) FROM norma;"
```

## Rollback de base de datos completo

Cuando la base de datos esta corrupta o hay datos erroneos masivos.

```bash
# 1. Parar todos los servicios que escriben en DB
docker compose -f infra/deploy/docker-compose.prod.yml stop worker-* api

# 2. Eliminar volumen de Postgres (ULTIMA RESORT)
docker compose -f infra/deploy/docker-compose.prod.yml down -v

# 3. Restaurar desde backup
gunzip -c /backups/esdata_20260425_030000.sql.gz | \
  docker compose -f infra/deploy/docker-compose.prod.yml exec -T postgres psql -U esdata esdata

# 4. Reconstruir schema si es necesario
docker compose -f infra/deploy/docker-compose.prod.yml exec api alembic upgrade head

# 5. Reiniciar servicios
docker compose -f infra/deploy/docker-compose.prod.yml up -d

# 6. Re-ingestion si faltan datos
docker compose -f infra/deploy/docker-compose.prod.yml run --rm worker-boe python boe.py --run-once
```

## Rollback de infraestructura (Docker)

Cuando hay problemas con las imagenes o configuracion de Docker.

```bash
# 1. Parar todo
docker compose -f infra/deploy/docker-compose.prod.yml down

# 2. Limpiar imagenes antiguas
docker image prune -f

# 3. Reconstruir desde limpio
docker compose -f infra/deploy/docker-compose.prod.yml build --no-cache
docker compose -f infra/deploy/docker-compose.prod.yml up -d

# 4. Verificar
docker compose -f infra/deploy/docker-compose.prod.yml ps
```

## Checklist de rollback

Antes de hacer deploy, verificar:

- [ ] Backup reciente disponible (verificar fecha)
- [ ] Tag/commit de version actual identificado
- [ ] Migraciones actuales son reversibles? (ver `docs/database.md`)
- [ ] Tiempo estimado de rollback comunicado al equipo

Durante el rollback:

- [ ] Parar todos los writers primero (workers, api)
- [ ] Restaurar DB antes de aplicar nueva version
- [ ] Verificar integridad despues de cada paso
- [ ] Monitorizar logs durante 10 minutos post-rollback

Post-rollback:

- [ ] Crear ticket para investigar causa raiz
- [ ] Documentar lecciones aprendidas
- [ ] Actualizar este documento si se encontro un gap

## Tiempos estimados de rollback

| Escenario | Tiempo estimado | Impacto |
|-----------|-----------------|---------|
| Rollback aplicacion sin schema | 2-5 min | API down ~1 min |
| Rollback migracion reversible | 5-10 min | API down ~2 min |
| Rollback migracion irreversible | 15-60 min | API down ~5 min + DB restore |
| Rollback DB completo | 30-120 min | API down ~10 min + re-ingestion |

## Referencias

- `docs/database.md` — estrategia de migraciones
- `docs/operations/README.md` — runbooks operativos
- `docs/infrastructure-handoff.md` — handoff completo

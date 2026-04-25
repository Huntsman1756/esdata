# Handoff to IT

## Objetivo

Este documento resume lo que IT necesita para mover `esdata` desde una prueba en VPS a un servidor corporativo o entorno gestionado mejor.

## Que es este servicio

`esdata` expone:

- API REST FastAPI para normativa, doctrina y modelos AEAT
- endpoint MCP HTTP privado en `/mcp`
- frontend web opcional
- workers de ingesta periodica

El endpoint MCP esta pensado para consumo por clientes LLM internos, no para exposicion publica abierta.

## Topologia recomendada

Minima:

- 1 host Linux
- Docker Compose
- Postgres local o gestionado
- proxy inverso interno o controlado
- acceso restringido al endpoint `/mcp`

Preferible en entorno corporativo:

- red privada o segmentada
- TLS terminado por proxy corporativo
- secretos fuera del repo
- sistema de backups gestionado

## Requisitos tecnicos

- Linux con Docker y Compose
- salida HTTPS hacia BOE, DGT, TEAC, AEAT y otras fuentes regulatorias
- volumen persistente para Postgres si no es servicio gestionado
- mecanismo de gestion de secretos

## Variables y secretos criticos

Minimo:

- `DATABASE_URL`
- `POSTGRES_PASSWORD` si Postgres es local
- `ESDATA_API_BASE_URL`
- `TEAC_SEED_URLS`
- `MCP_API_KEY`
- `MCP_RATE_LIMIT_PER_MINUTE`

Recomendacion:

- no almacenar secretos en el repo
- no exponer `MCP_API_KEY` en frontend ni en variables publicas
- versionar un `.env.example`, no el `.env` real

## Contenedores importantes

- `api`
- `postgres`
- `web`
- `caddy`
- `worker-boe`
- `worker-dgt`
- `worker-teac`
- `worker-modelos`

Workers adicionales documentales pueden habilitarse segun necesidad.

## Seguridad minima requerida

Para `/mcp`:

1. `MCP_API_KEY` obligatoria en produccion
2. `MCP_RATE_LIMIT_PER_MINUTE` configurado
3. acceso solo desde red privada, VPN o proxy con restriccion

No se recomienda:

- publicar `/mcp` abierto a Internet
- usar la misma key en demasiados clientes sin control
- depender solo de ofuscacion por URL

## Despliegue

Referencia principal:

- `infra/deploy/docker-compose.prod.yml`
- `docs/operations/runbooks/deploy-compose.md`
- `docs/deployment/vps-trial-deploy.md`

Orden recomendado:

1. preparar secretos y variables
2. validar compose
3. levantar `postgres` y `api`
4. validar salud API
5. validar `/mcp` con `API key`
6. levantar `web` si aplica
7. levantar workers necesarios

## Checklist de aceptacion

### Salud basica

- `GET /health` responde `200`
- `GET /status` responde `200`
- `docker compose ps` sin servicios en restart loop

### MCP privado

- `/mcp` devuelve `401` sin `X-API-Key` cuando `MCP_API_KEY` esta configurada
- `/mcp` permite `initialize` y `tools/list` con la key correcta
- el rate limit devuelve `429` si se excede el umbral

### Datos y workers

- Postgres persistente y con tablas inicializadas
- workers principales con logs sanos
- fuentes externas accesibles

### Operacion

- logs accesibles para API y workers
- backup de Postgres definido
- procedimiento de restart documentado

## Verificaciones recomendadas

En el repo:

```bash
pytest apps/api/tests/test_mcp_private.py -q
pytest apps/api/tests/test_smoke.py -q
```

En el entorno desplegado:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/status
curl -i -H "Accept: text/event-stream" -H "X-API-Key: $MCP_API_KEY" http://127.0.0.1:8000/mcp
```

## Riesgos conocidos

- workers dependen de fuentes externas que pueden cambiar HTML o disponibilidad
- el endpoint MCP HTTP depende de `fastapi-mcp`; conviene mantener smoke tests E2E reales
- la semantica de algunas variables de workers necesita revisiones futuras, especialmente alrededor de `DGT_SSL_VERIFY`

## Que no debe asumir IT

- que Railway siga siendo la plataforma de referencia
- que `/mcp` deba ser publico
- que el frontend sea obligatorio para validar MCP

## Referencias

- `docs/deployment/vps-trial-deploy.md`
- `docs/operations/OPERATIONS.md`
- `docs/environment-variables.md`
- `infra/deploy/docker-compose.prod.yml`

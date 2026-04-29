# FAQ y troubleshooting

## La API responde pero no devuelve datos utiles

Comprobar:

- que la base de datos este conectada con `/health`
- que los workers hayan corrido al menos una vez
- que la fuente o dominio consultado este realmente cubierto por el repo
- que no estes consultando una fase futura aun no implementada

## `/health` devuelve DB desconectada

Revisar:

- `DATABASE_URL`
- estado del contenedor `postgres`
- conectividad entre `api` y `postgres`

Comandos utiles:

```bash
docker compose -f infra/deploy/docker-compose.prod.yml ps
docker compose -f infra/deploy/docker-compose.prod.yml logs api
docker compose -f infra/deploy/docker-compose.prod.yml logs postgres
```

## `/status` muestra workers stale o never_run

Eso suele indicar que el worker no ha ejecutado correctamente o no ha corrido nunca.

Pasos utiles:

```bash
docker compose -f infra/deploy/docker-compose.prod.yml logs worker-boe
docker compose -f infra/deploy/docker-compose.prod.yml run --rm worker-boe python boe.py --run-once
```

Aplicar el mismo patron al worker que corresponda.

## La UI web no carga datos

Revisar:

- que `ESDATA_API_BASE_URL` apunte a la API correcta
- que el contenedor `web` este sano
- que la API responda desde la red del frontend

Comandos utiles:

```bash
docker compose -f infra/deploy/docker-compose.prod.yml logs web
docker compose -f infra/deploy/docker-compose.prod.yml restart web
```

## `/mcp` devuelve 401

Lo normal es que falte la API key o sea incorrecta.

Revisar:

- `MCP_API_KEY`
- cabecera `X-API-Key`

Ejemplo:

```bash
curl -s http://127.0.0.1:8000/mcp -H "X-API-Key: secret"
```

## `/mcp` devuelve 429

Se ha alcanzado el limite configurado por `MCP_RATE_LIMIT_PER_MINUTE`.

Opciones:

- reducir frecuencia del cliente
- aumentar el limite si el caso de uso lo justifica
- poner cache o batching en el cliente

## Alembic no aplica migraciones

Revisar:

- que la API o el contenedor ops tenga acceso a DB
- que la revision actual y `head` sean coherentes

Comandos utiles:

```bash
docker compose -f infra/deploy/docker-compose.prod.yml up -d postgres
docker compose -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic current
docker compose -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic history
docker compose -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic upgrade head
```

## No se que superficie debo usar

Guia rapida:

- usa `API` si integras con otro backend o automatizacion propia
- usa `MCP` si el consumidor es un cliente MCP o un LLM
- usa la UI web si quieres consulta humana rapida o ver paneles internos

## El manual dice una cosa y el roadmap otra

Para estado vivo, manda siempre:

```text
docs/master-execution-roadmap.md
```

El manual explica capacidades, uso y limites. El roadmap manda sobre fase activa, estado y siguiente paso exacto.

## Referencias utiles

- `../operations/README.md`
- `../deployment/overview.md`
- `../master-execution-roadmap.md`

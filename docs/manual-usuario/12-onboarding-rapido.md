# Onboarding rapido

## Objetivo

Esta guia sirve para tener `esdata` operativo y entendible en pocos minutos.

## Ruta corta de 5 minutos

1. Leer `01-que-es-esdata-y-que-incluye.md`.
2. Confirmar que tu caso encaja con `05-limites-alcance-y-estado-actual.md`.
3. Levantar el stack con Docker Compose.
4. Verificar `/health` y `/status`.
5. Probar una busqueda o una consulta de modelo.

## Arranque minimo

Levantar el stack:

```bash
docker compose -f infra/deploy/docker-compose.prod.yml up -d
```

Aplicar migraciones:

```bash
docker compose -f infra/deploy/docker-compose.prod.yml up -d postgres
docker compose -f infra/deploy/docker-compose.prod.yml --profile ops run --rm ops alembic upgrade head
```

Verificar salud:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/status
```

## Primera comprobacion funcional

Busqueda legislativa:

```bash
curl -G -s http://127.0.0.1:8000/v1/buscar --data-urlencode "q=iva intracomunitario"
```

Modelo AEAT:

```bash
curl -s http://127.0.0.1:8000/v1/modelos/303
```

Obligaciones aplicables:

```bash
curl -G -s http://127.0.0.1:8000/v1/obligaciones/aplicables --data-urlencode "tipo_entidad=sociedad_valores"
```

## Si vas a usar la UI

Abre:

- `/`
- `/buscar`
- `/admin/cambios`
- `/admin/workflow`

## Si vas a integrar por API

Empieza por:

- `06-api-y-ejemplos.md`
- `09-referencia-de-endpoints.md`
- `../openapi-gpt.json`

## Si vas a integrar por MCP

Empieza por:

- `07-mcp-y-clientes.md`

Y decide si tu cliente necesita:

- HTTP en `/mcp`
- o `stdio`

## Si algo falla

Ir a:

- `08-faq-y-troubleshooting.md`
- `../operations/README.md`

## Regla practica final

No intentes abarcar todo el repo desde el primer dia.

Empieza por la superficie que realmente vayas a usar:

- UI
- API
- MCP
- operacion tecnica

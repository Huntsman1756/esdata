# Logging

## Objetivo

Definir una pauta minima de revision de logs para `esdata` en despliegues privados.

## Que revisar

### API

Buscar:

- errores `500`
- `401` repetidos en `/mcp`
- `429` repetidos en `/mcp`
- timeouts o errores de DB

Comando:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml logs -f api
```

### Workers

Buscar:

- reinicios repetidos
- errores de parseo
- caidas de fuentes externas
- ciclos sin progreso

Comando:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml logs -f worker-boe worker-dgt worker-teac worker-modelos
```

### Postgres

Buscar:

- rechazos de conexion
- reinicios
- corrupcion o problemas de disco

Comando:

```bash
docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml logs -f postgres
```

## Frecuencia minima

- durante pruebas: revisar tras cada cambio importante
- en uso estable: revisar cuando falle un smoke test o un healthcheck

## Politica minima de logging

- no loggear secretos
- no loggear `X-API-Key`
- no loggear bodies completos de peticiones potencialmente sensibles
- conservar logs operativos el tiempo minimo necesario para operar y depurar

## Alertas utiles

Minimo razonable:

- alertar si `/health` falla
- alertar si un contenedor reinicia repetidamente
- alertar si `/mcp` acumula muchos `401`, `429` o `500`

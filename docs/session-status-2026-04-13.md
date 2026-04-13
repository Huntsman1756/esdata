# Estado de sesion a 2026-04-13

## Resumen rapido

- GitHub actualizado en `main` hasta `d150b06`.
- Railway operativo en todos los servicios principales y cron configurados.
- API publica viva en `https://esdata-production.up.railway.app`.
- OpenAPI publica viva en `https://esdata-production.up.railway.app/openapi.json`.
- Frontend publico vivo en `https://web-production-ecb5.up.railway.app`.
- Modelos AEAT v2 desplegados con campañas, casillas, claves, instrucciones y normativa.
- Specs reducidas para GPT disponibles en el repo:
  - `docs/openapi-gpt.json`
  - `docs/openapi-gpt-3.0.json`

## Commits relevantes de esta sesion

| Commit | Mensaje |
| --- | --- |
| `40210b2` | `fix(railway): use service-root deploy flow` |
| `f7b6f29` | `feat(modelos): complete campaign-aware API and GPT spec` |
| `d150b06` | `docs(repo): sync README with Railway and GPT surfaces` |

## GitHub

- Rama local y remota alineadas.
- Verificado con:

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
```

- Estado final observado:
  - `## main...origin/main`
  - `HEAD == origin/main`

## Railway

### Servicios en verde

- `esdata`
- `worker-boe`
- `cron-boe-daily`
- `worker-dgt`
- `cron-dgt-weekly`
- `worker-teac`
- `cron-teac-weekly`
- `worker-modelos`
- `cron-modelos-daily`
- `web`
- `Postgres`

### Acciones hechas en Railway durante esta sesion

- Se corrigio el flujo de deploy de `esdata` para evitar el error de `rootDirectory` duplicado.
- Se repararon `worker-dgt`, `worker-teac`, `cron-dgt-weekly` y `cron-teac-weekly` redeployando desde `apps/workers` como raiz del artefacto.
- Se crearon en Railway los servicios inexistentes:
  - `worker-modelos`
  - `cron-modelos-daily`
- Se anadieron variables minimas a los servicios de modelos:
  - `APP_ENV=production`
  - `DATABASE_URL=...`
  - `LOG_LEVEL=INFO`
  - `WORKER_RETRY_MAX=3`
  - `MODELOS_SYNC_INTERVAL=86400` en `worker-modelos`

## Verificaciones frescas hechas al final

```bash
curl https://esdata-production.up.railway.app/health
curl https://esdata-production.up.railway.app/openapi.json
railway status --json
```

Resultado observado:

- `/health` -> `{"status":"ok"}`
- `/openapi.json` responde con OpenAPI `3.1.0`
- `info.title = "esdata API"`
- `info.version = "0.1.6"`

## Lo que ya esta hecho en producto/codigo

- API tipada con `response_model` para endpoints clave de legislacion, doctrina y modelos.
- OpenAPI utilizable para GPT Actions.
- Export de spec reducida para GPT con `scripts/export-gpt-openapi.py`.
- Modelos AEAT v2 con:
  - versionado por campaña
  - casillas
  - claves
  - instrucciones
  - normativa
  - relacion con articulos y doctrina
- Frontend con detalle de modelo y seleccion de campaña.
- Worker de modelos desplegado en Railway.

## Pendiente recomendado para la proxima sesion

### Producto / posicionamiento

1. Decidir el enfoque comercial inicial:
   - infraestructura para agentes fiscales
   - API para software fiscal
   - copiloto para despachos
2. Definir una propuesta de valor corta y una landing simple.
3. Decidir si el siguiente entregable visible sera:
   - conector GPT / MCP publico
   - demo para despachos
   - skillset propio por rol fiscal

### GPT / MCP

1. Probar import real de `openapi-gpt.json` o `/openapi.json` en el builder de ChatGPT.
2. Si el builder falla con 3.1, usar `docs/openapi-gpt-3.0.json`.
3. Valorar publicar una URL MCP mas visible/documentada si quieres posicionarte como herramienta para agentes.

### Datos / cobertura

1. Revisar si `ITPAJD` sigue bloqueada por el fetch de metadata BOE y decidir si se parchea o se deja fuera de cobertura por ahora.
2. Medir cobertura real de modelos v2 en produccion:
   - cuantos modelos tienen casillas
   - cuantos tienen claves
   - cuantos tienen instrucciones
3. Anadir smoke checks de modelos al workflow si quieres detectar roturas antes.

### Calidad / operacion

1. Revisar el warning de Pydantic V2.11 antes de que escale a deuda real.
2. Revisar la vulnerabilidad moderada que GitHub ha marcado en la rama por defecto.
3. Valorar una comprobacion periodica real de cron con `sync_log` y alertas minimas.

## Riesgos o notas

- `docs/production-status-2026-04-12.md` ya no refleja el estado final actual de Railway ni de modelos v2; tomar este archivo como referencia mas fiable para retomar trabajo.
- El proyecto ya es util como infraestructura, pero todavia falta empaquetado de producto para competir por adopcion, no solo por capacidad tecnica.

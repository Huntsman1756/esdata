# Diseno: MCP Fase 5.3 - Alinear env vars reales con runtime

## Objetivo

Alinear `infra/deploy/docker-compose.prod.yml`, `infra/deploy/compose.env.example` y `docs/environment-variables.md` para que la documentacion y la plantilla de despliegue reflejen las variables de entorno que el runtime Compose usa de verdad hoy.

Esta fase no intenta redisenar la configuracion completa ni eliminar todas las variables historicas del repo. Su trabajo es mas concreto:

- fijar `compose.env.example` como plantilla del despliegue Compose activo
- usar `docker-compose.prod.yml` como fuente operativa de verdad para el runtime activo
- dejar `docs/environment-variables.md` como inventario global, pero etiquetado por estado de cableado real

## Contexto

El plan MCP fija en `5.3` que toca alinear env vars reales con runtime.

Estado actual observado:

- `infra/deploy/docker-compose.prod.yml` ya expresa el runtime Compose real, incluyendo API, web, workers, crons, `ops`, backup y observabilidad
- `infra/deploy/compose.env.example` arrastra variables que no forman parte del deploy activo o que ya no deben venderse como verdad de runtime, por ejemplo `NEXT_PUBLIC_API_BASE_URL`
- `docs/environment-variables.md` mezcla en las mismas tablas variables del deploy Compose activo, variables usadas solo por codigo o tests, y variables no cableadas al despliegue actual, sin etiquetado suficiente

El hueco real no es solo documental: hoy es posible leer el ejemplo o la documentacion y creer que ciertas variables forman parte del runtime Compose activo cuando en realidad no estan cableadas, o al reves, pasar por alto variables del deploy activo que solo se descubren leyendo `docker-compose.prod.yml`.

## Alcance aprobado

Incluye:

- revisar `infra/deploy/docker-compose.prod.yml` como fuente de verdad del runtime Compose activo
- reducir `infra/deploy/compose.env.example` a variables del despliegue Compose activo y a inputs operativos inmediatos de ese despliegue
- actualizar `docs/environment-variables.md` para mantener inventario global pero con estado por variable
- actualizar `docs/master-execution-roadmap.md`
- anadir nota reusable en `docs/operations/agent-notes.md` si emerge una regla clara sobre env vars activas vs no cableadas

No incluye:

- redisenar el sistema de configuracion de la app
- introducir un schema formal de settings para todo el repo
- eliminar variables historicas del codigo si aun existen fuera del deploy activo
- tocar secretos reales o procesos de rotacion
- convertir esta fase en un cleanup agresivo de todas las variables del repo

## Enfoques considerados

### Opcion 1 - inventario global con estado por variable

Mantener `docs/environment-variables.md` como inventario global, pero etiquetar cada variable con su estado real de cableado.

Estados aprobados para esta fase:

- `runtime deploy`
- `code-only`
- `legacy/no cableada`

Ventajas:

- preserva contexto util sin mentir sobre el runtime activo
- mejora el handoff operativo sin borrar informacion tecnica valida
- permite que `compose.env.example` se mantenga limpio sin perder trazabilidad documental

Inconvenientes:

- requiere revisar variable por variable y mantener la clasificacion actualizada

### Opcion 2 - documentacion solo del runtime activo

Reducir `docs/environment-variables.md` a variables del deploy Compose actual.

Ventajas:

- lectura muy simple para ops

Inconvenientes:

- pierde contexto sobre variables reales usadas por codigo o tests fuera del deploy activo
- obliga a buscar en codigo para entender por que existe una variable no documentada en runtime

### Opcion 3 - limpieza agresiva del example y la documentacion

Ademas de documentar el runtime activo, eliminar del `compose.env.example` y de la documentacion cualquier variable no usada por Compose actual.

Ventajas:

- maxima higiene del template

Inconvenientes:

- mayor riesgo de borrar contexto operativo todavia util para tareas manuales o validaciones futuras
- mas churn del necesario para `5.3`

## Decision aprobada

Se aprueba la opcion 1.

`compose.env.example` reflejara el deploy Compose activo. `docs/environment-variables.md` seguira siendo inventario global, pero cada variable quedara marcada por su estado real de cableado.

## Fuente de verdad aprobada

Para `5.3`, la jerarquia operativa queda asi:

1. `infra/deploy/docker-compose.prod.yml` define que variables forman parte del runtime Compose activo
2. `infra/deploy/compose.env.example` lista la plantilla de valores esperados para ese runtime
3. `docs/environment-variables.md` explica y clasifica el conjunto completo de variables conocidas

Si una variable no aparece en `docker-compose.prod.yml`, no debe venderse como `runtime deploy` salvo que exista una razon operativa explicita en esta misma fase.

## Clasificacion aprobada

### `runtime deploy`

Variables cableadas hoy al despliegue Compose activo, ya sea en servicios base, workers, crons, backup, `ops` u observabilidad.

Ejemplos observados:

- `DATABASE_URL`
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`, `POSTGRES_BIND_ADDRESS`
- `API_DOMAIN`, `WEB_DOMAIN`, `CADDY_EMAIL`
- `APP_ENV`, `ESDATA_API_KEY`, `MCP_API_KEY`, `ESDATA_API_BASE_URL`
- variables de workers activas en Compose (`BOE_API_BASE`, `BOE_LEGISLACION_NORMAS`, `TEAC_SEED_URLS`, `BDNS_SEED_URLS`, `BORME_SEED_URLS`, `CNMV_SEED_URLS`, `SEPBLAC_SEED_URLS`, `CENDOJ_SEED_URLS`, `BDE_SEED_URLS`, `AEPD_SEED_URLS`, `DGT_SSL_VERIFY`, `DGT_DISCOVERY`, `MODELOS_SYNC_INTERVAL`, `WORKER_REQUEST_DELAY`, etc.)
- variables activas de cron/ops/observabilidad en Compose (`HC_PING_URL_*`, `GRAFANA_ADMIN_PASSWORD`, `GRAFANA_ROOT_URL`, etc.)

### `code-only`

Variables referenciadas por codigo o tests pero no inyectadas por el deploy Compose activo.

Ejemplos plausibles en esta fase:

- `ESDATA_CORS_ORIGINS`
- `ESDATA_RATE_LIMIT_ENABLED`
- `ESDATA_HSTS_ENABLED`
- `ESDATA_SENTRY_DSN`
- `AGENT_MONITOR_*`
- `DATABASE_PUBLIC_URL`
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`
- `LOG_LEVEL`, `LOG_FORMAT`, `SLACK_WEBHOOK_URL`, `REDIS_URL`, `SECRET_KEY`

Estas variables no desaparecen de la documentacion, pero dejan de presentarse como parte del deploy Compose activo si Compose no las pasa hoy.

### `legacy/no cableada`

Variables heredadas, ambiguas o no alineadas con el deploy activo.

Ejemplo confirmado para esta fase:

- `NEXT_PUBLIC_API_BASE_URL`

Esta variable no debe seguir viva en `compose.env.example` del deploy Compose activo y debe quedar marcada en docs como no valida para el runtime activo.

## Reglas de cambio por archivo

### `infra/deploy/docker-compose.prod.yml`

- solo se toca si hay una discrepancia operativa real entre las variables requeridas/default y el runtime esperado
- si el archivo ya refleja correctamente el runtime activo, puede quedar sin cambios funcionales y actuar como fuente de clasificacion

### `infra/deploy/compose.env.example`

- debe quedar centrado en variables del deploy Compose activo
- no debe contener variables cliente-side ni restos de configuracion ya retirados del runtime activo
- no debe actuar como inventario historico del repo

### `docs/environment-variables.md`

- debe indicar que `compose.env.example` es la plantilla del deploy Compose activo
- debe separar claramente runtime activo, code-only y legacy/no cableada
- no debe seguir vendiendo como `runtime deploy` variables que Compose no pasa hoy

## Contrato aprobado para 5.3

Tras esta fase:

- una variable listada como `runtime deploy` debe aparecer en `docker-compose.prod.yml`
- una variable no presente en `docker-compose.prod.yml` no puede quedar presentada como activa de deploy sin justificacion explicita
- `compose.env.example` no debe contener `NEXT_PUBLIC_API_BASE_URL`
- `docs/environment-variables.md` debe dejar visible que `NEXT_PUBLIC_API_BASE_URL` es heredada/no cableada y no valida para el deploy activo

## Testing y verificacion aprobados

La fase requiere verificaciones operativas pequenas, no una nueva capa compleja de tooling.

Minimo:

1. validar que `docker-compose.prod.yml` y `compose.env.example` siguen siendo consistentes para `docker compose config`
2. comprobar que la documentacion editada no contradice `docker-compose.prod.yml`
3. verificar que `docs/README.md` y `master-execution-roadmap.md` no se contradicen

Si emerge una verificacion automatizable pequena y barata, puede anadirse, pero no es obligatoria para aprobar el diseno.

## Riesgos y limites

- seguiran existiendo variables fuera del deploy activo que el codigo conoce; esta fase no las elimina del repo
- puede haber surfaces manuales o locales que usen variables no cableadas por Compose; en `5.3` se documentan como tales, no se promocionan a runtime activo
- el inventario exigira mantenimiento si nuevas fases anaden variables al deploy real

## Resultado esperado

Tras `5.3`, un operador que lea `docker-compose.prod.yml`, `compose.env.example` y `docs/environment-variables.md` debe poder distinguir sin ambiguedad:

- que variables necesita el despliegue Compose activo
- que variables existen solo en codigo/tests y no las inyecta Compose hoy
- que variables son heredadas o ya no deben usarse en el runtime activo

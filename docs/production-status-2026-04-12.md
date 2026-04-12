# Estado operativo a 2026-04-12

## Resumen

- Produccion Railway operativa en `https://esdata-production.up.railway.app`.
- BOE, DGT y TEAC activos en produccion.
- Frontend Next.js operativo en `https://web-production-ecb5.up.railway.app`.
- Nueva capa **Modelos AEAT** desplegada:
  - 11 modelos: 100, 111, 115, 130, 180, 187, 190, 193, 196, 303, 390
  - 27 relaciones modelo-articulo con fuente oficial verificable
  - 3 nuevos endpoints API: `GET /v1/modelos`, `GET /v1/modelos/{codigo}`, `GET /v1/modelos/{codigo}/articulos`
  - Sidebars "Modelos AEAT relacionados" en detalle de articulo y doctrina
  - Pagina de detalle de modelo: `/modelo/[codigo]`
- Validacion manual post-despliegue repetida sin regresiones:
  - DGT: 21 links, 0 low confidence
  - TEAC: 4 links, 0 low confidence

## Lo hecho en esta sesion

### Capa Modelos AEAT — Fase 1

**Batch A: Schema + Seed**
- `infra/sql/003_modelos_aeat.sql`: tablas `aeat_modelo` y `modelo_articulo`
  - Cada relacion requiere `fuente` y `url_fuente` (no hay relaciones sin fuente)
- `scripts/seed-modelos.py`: carga idempotente con modo `--dry-run`
  - 6 modelos con metadata de paginas AEAT oficiales
  - 16 relaciones verificables con instrucciones oficiales de modelos
- Migracion aplicada en produccion, seed ejecutado

**Batch B: API**
- `apps/api/routers/modelos.py`: 3 endpoints
  - `GET /v1/modelos` — lista con conteo de articulos
  - `GET /v1/modelos/{codigo}` — detalle con articulos + doctrina derivada
  - `GET /v1/modelos/{codigo}/articulos` — solo articulos
- Cada articulo devuelve: norma, numero, titulo, casilla, nota, **fuente**, **url_fuente**
- `doctrina_relacionada` derivada solo por join real: modelo → articulo → doctrina
- 5 nuevos tests en `test_smoke.py` (28 passing total)

**Batch C: Frontend — Sidebars**
- `ModeloList` en sidebar de detalle de articulo
- `DoctrinaModelos` en sidebar de detalle de doctrina (derivado de articulos enlazados, dedupeado por codigo)
- `modelo-badge.tsx`: componente compacto con link a `/modelo/{codigo}`

**Batch D: Frontend - Detalle modelo**
- `/modelo/[codigo]`: pagina completa
  - Identidad: badge AEAT, codigo, impuesto, periodo
  - Link "Ver en sede AEAT"
  - Lista de articulos con casilla, nota, fuente y link a fuente
  - Sidebar con doctrina relacionada

**Expansion posterior de Modelos AEAT**
- Se ampliaron modelos verificables hasta cubrir 11 codigos:
  - `180`, `187`, `190`, `193`, `196` anadidos sobre la base inicial
- Estado consolidado actual:
  - 11 modelos en `aeat_modelo`
  - 27 relaciones en `modelo_articulo`
  - Excluidos documentados por falta de encaje o fuente clara: `198`, `216`, `289`, `290`, `296`

### UX Polish anterior (sesiones previas)

- Home con posicionamiento: "Encuentra criterio fiscal aplicable, no solo texto legal."
- Search UX ajustada: placeholder "Conceptos fiscales, articulos, doctrina..." + helper text
- Ejemplos de busqueda con resultados reales
- Confidence badge textual (no numeros crudos)
- Deduplicacion de resultados de busqueda (`DISTINCT ON`)

## Estado actual verificado

### API / workers
- `api`: ok
- `worker-boe`: ok
- `worker-dgt`: ok
- `worker-teac`: ok
- Ultima comprobacion manual en `/status`:
  - `worker-boe.last_run`: `2026-04-12T15:00:58.214957+00:00`
  - `worker-dgt.last_run`: `2026-04-12T14:57:50.679063+00:00`
  - `worker-teac.last_run`: `2026-04-12T14:57:01.122307+00:00`
- `cron-boe-daily`: `never_run`
- `cron-dgt-weekly`: `never_run`
- `cron-teac-weekly`: `never_run`

### Frontend
- Home: ok (cobertura + estado + busqueda)
- /buscar: ok (resultados legislacion y doctrina)
- /articulo/[norma]/[numero]: ok (detalle + historial + modelos AEAT)
- /doctrina/[...referencia]: ok (detalle + articulos + modelos AEAT)
- /modelo/[codigo]: ok (detalle de modelo + articulos + doctrina derivada)

### Datos
- Cobertura legislativa:
  - LGT: 319 articulos
  - LIRPF: 174 articulos
  - LIS: 180 articulos
  - LIVA: 228 articulos
  - Total: 901 articulos, 941 versiones
- Modelos AEAT:
  - 11 modelos en `aeat_modelo`
  - 27 relaciones en `modelo_articulo` (todas con fuente)
- Baseline de enlazado pre-cron:
  - DGT: 21 links, 0 low confidence
  - TEAC: 4 links, 0 low confidence
- Revalidacion manual `scripts/validate-cron-run.py --after 2026-04-12`:
  - DGT: 21 links, 0 low confidence
  - TEAC: 4 links, 0 low confidence
  - Documentos recientes desde `2026-04-12`: 0

## Estado de commits

| Commit | Descripcion |
| --- | --- |
| 879bef4 | feat(aeat-modelos): Phase 1 — schema, seed, and spec |
| 307dae9 | feat(aeat-modelos): Batch B — API endpoints + tests |
| 8b69b9f | feat(web): Batch C — modelos sidebars en articulo y doctrina |
| 37a2f3e | feat(web): Batch D — modelo detail page |
| 9964414 | feat(aeat-modelos): add models 190 and 196 with verified sources |

## Pendiente para la proxima sesion

### Operativo (plan original)
1. Esperar la primera ejecucion real de `cron-teac-weekly`
2. Esperar la primera ejecucion real de `cron-dgt-weekly`
3. Repetir validacion via `/status` y `scripts/validate-cron-run.py` cuando esos cron dejen de estar en `never_run`

### Verificado en esta sesion
1. `/status` sigue mostrando `cron-dgt-weekly` y `cron-teac-weekly` en `never_run`
2. Los workers manuales si muestran ejecuciones recientes y estado `ok`
3. `scripts/validate-cron-run.py --after 2026-04-12` sigue limpio, sin regresiones ni low confidence

### Proximo ciclo de mejora TEAC/DGT
1. Consultar casos con `confianza_enlace < 1.0` post-cron
2. Agrupar por patron real
3. Elegir un solo slice pequeno
4. Implementar matcher/fix minimo
5. Verificar en produccion

## Deuda tecnica anotada

1. **N+1 en sidebars de modelos**: `ModeloList` y `DoctrinaModelos` hacen fetch por cada modelo. Aceptable para 6 modelos. Consolidar en endpoint dedicado o helper server-side cuando haya mas cobertura.
2. **Busqueda de legislacion**: no soporta preguntas en lenguaje natural. Placeholder y helper text ajustados para gestionar expectativas. Mejora futura: ranking semantico o query expansion.

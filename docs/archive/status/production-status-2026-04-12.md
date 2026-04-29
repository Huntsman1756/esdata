# Estado operativo a 2026-04-12

## Resumen

- Produccion Railway operativa en `https://esdata-production.up.railway.app`.
- BOE, DGT y TEAC activos en produccion.
- Frontend Next.js operativo en `https://web-production-ecb5.up.railway.app`.
- Nueva capa **Modelos AEAT** desplegada:
  - 8 modelos: 100, 111, 115, 130, 190, 196, 303, 390
  - 22 relaciones modelo-articulo con fuente oficial verificable
  - 3 nuevos endpoints API: `GET /v1/modelos`, `GET /v1/modelos/{codigo}`, `GET /v1/modelos/{codigo}/articulos`
  - Sidebars "Modelos AEAT relacionados" en detalle de articulo y doctrina
  - Pagina de detalle de modelo: `/modelo/[codigo]`

## Lo hecho en esta sesion

### Slice ITPAJD pendiente de verificacion desplegada

- `apps/web/lib/types.ts`: `Norma` alineada con `tipo_documento` y `estado_cobertura`.
- `apps/web/app/page.tsx`: home actualizada para reflejar el soporte actual del slice con `ITPAJD` y sacar `ITP y AJD` de la lista de trabajo futuro.
- `README.md`: cobertura del slice actualizada para incluir `ITPAJD`, dejando explicito que la verificacion desplegada sigue pendiente.
- Estado actual: cambios alineados en tipos, copy y configuracion del slice; falta ejecutar el smoke de Task 5 en Railway antes de marcar `ITPAJD` como verificado en produccion.

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

**Batch D: Frontend — Detalle modelo**
- `/modelo/[codigo]`: pagina completa
  - Identidad: badge AEAT, codigo, impuesto, periodo
  - Link "Ver en sede AEAT"
  - Lista de articulos con casilla, nota, fuente y link a fuente
  - Sidebar con doctrina relacionada

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
  - 8 modelos en `aeat_modelo`
  - 22 relaciones en `modelo_articulo` (todas con fuente)
- Baseline de enlazado pre-cron:
  - DGT: 21 links, 0 low confidence
  - TEAC: 4 links, 0 low confidence

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
3. Confirmar via `/status` y `scripts/validate-cron-run.py` que esas corridas no introducen regresiones

### Proximo ciclo de mejora TEAC/DGT
1. Consultar casos con `confianza_enlace < 1.0` post-cron
2. Agrupar por patron real
3. Elegir un solo slice pequeno
4. Implementar matcher/fix minimo
5. Verificar en produccion

## Deuda tecnica anotada

1. **N+1 en sidebars de modelos**: `ModeloList` y `DoctrinaModelos` hacen fetch por cada modelo. Aceptable para 6 modelos. Consolidar en endpoint dedicado o helper server-side cuando haya mas cobertura.
2. **Busqueda de legislacion**: no soporta preguntas en lenguaje natural. Placeholder y helper text ajustados para gestionar expectativas. Mejora futura: ranking semantico o query expansion.

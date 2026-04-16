# Next Session Handoff — 2026-04-16

## Estado al cerrar esta sesion

- `main` esta limpio y alineado con `origin/main`.
- El bloque regulatorio de Fase 0 y Fase 1 ha quedado arrancado y ya esta publicado en GitHub.
- La expansion regulatoria ya no esta solo planificada: ahora existen slices funcionales para `CNMV`, `SEPBLAC` y una primera capa de `obligacion_regulatoria`.

## Commits relevantes ya en `main`

- `78be5f3` `docs(plan): add regulatory compliance expansion roadmap`
- `8853e9e` `docs(plan): add compliance corpus master inventory`
- `e568163` `feat(cnmv): add regulatory document ingestion and API`
- `ba9d356` `feat(sepblac): add operational document ingestion and API`
- `e1d658a` `feat(obligaciones): add initial regulatory obligations layer`

## Lo que si quedo resuelto

### Plan y canonizacion del corpus

- Plan maestro permanente creado en:
  - `docs/regulatory-compliance-expansion-plan.md`
- Fase 0 cerrada con inventario maestro y canonizacion inicial del corpus regulatorio.
- El corpus ya esta separado por fuente:
  - `UE`
  - `BOE`
  - `CNMV`
  - `SEPBLAC`

### Slice `CNMV`

- Worker nuevo:
  - `apps/workers/cnmv.py`
- API nueva:
  - `GET /v1/cnmv`
  - `GET /v1/cnmv/{referencia}`
- Persistencia en `documento_interpretativo` con:
  - `organismo_emisor='CNMV'`
  - `tipo_fuente='cnmv'`
- Clasificacion heuristica minima de:
  - `tipo_documento`
  - `ambito`
- Integrado en:
  - `main.py`
  - `/status`
  - `docker-compose`
  - `infra/deploy`
  - workflow de Railway
  - `scripts/smoke-check.py`

### Slice `SEPBLAC`

- Worker nuevo:
  - `apps/workers/sepblac.py`
- API nueva:
  - `GET /v1/sepblac`
  - `GET /v1/sepblac/{referencia}`
- Soporte mixto de extraccion:
  - HTML
  - PDF
- Persistencia en `documento_interpretativo` con:
  - `organismo_emisor='SEPBLAC'`
  - `tipo_fuente='sepblac'`
- `Modelo 19` tratado como formulario operativo en este primer slice.

### Capa `obligacion_regulatoria`

- Nuevas tablas base:
  - `obligacion_regulatoria`
  - `obligacion_documento`
- Integradas tanto en:
  - `apps/workers/boe.py` (bootstrap compartido)
  - baseline Alembic `20260416_0001`
- API nueva:
  - `GET /v1/obligaciones`
  - `GET /v1/obligaciones/{codigo}`
- Seeds minimos ya cubiertos en tests para:
  - `CNMV-IR-RESERVADA`
  - `SEPBLAC-INDICIO-M19`
- La capa ya expone:
  - codigo
  - fuente
  - tipo de obligacion
  - sujeto obligado
  - periodicidad
  - modelo/reporte
  - documento origen
  - documentos relacionados

## Validaciones que si pasaron

### CNMV

- `ruff` sobre Python modificado: OK
- `pytest apps/api/tests/ apps/workers/tests/test_cnmv.py -q`: `45 passed`

### SEPBLAC

- `ruff` sobre Python modificado: OK
- `pytest apps/api/tests/ apps/workers/tests/test_sepblac.py -q`: `46 passed`

### Obligaciones

- `ruff` sobre el slice de obligaciones: OK
- `pytest apps/api/tests/test_smoke.py -q`: `44 passed`

## Estado de produccion real al cerrar la sesion

- No se ha hecho verificacion manual adicional en Railway o en la API publica despues de estos ultimos pushes.
- Lo que si esta hecho es dejar preparado todo para deploy/cron/smoke del nuevo bloque regulatorio:
  - `worker-cnmv`
  - `cron-cnmv-weekly`
  - `worker-sepblac`
  - `cron-sepblac-weekly`
  - smoke checks de:
    - `/v1/cnmv`
    - `/v1/sepblac`
    - `/v1/obligaciones`

## Siguiente paso recomendado para la proxima sesion

No conviene volver a abrir arquitectura desde cero. El siguiente paso natural es uno de estos dos:

1. **Ampliar obligaciones usando mas referencias canonizadas**
   - anadir nuevas obligaciones derivadas de:
     - `Circular 1/2010`
     - `Circular 3/2014`
     - `Circular 4/2018`
     - `Ley 10/2010`
     - `RD 304/2014`
   - objetivo: enriquecer `obligacion_regulatoria` sin cambiar el modelo base

2. **Empezar troceado de documentos**
   - secciones
   - disposiciones adicionales
   - anexos
   - objetivo: derivar obligaciones con menos heuristica y mas trazabilidad

### Recomendacion concreta

Empezar por la opcion `1`.

Motivo:

- el modelo minimo ya existe
- `CNMV` y `SEPBLAC` ya tienen superficie API
- el siguiente ROI es poblar mejor `obligacion_regulatoria`
- el troceado documental es util, pero complica mas y conviene hacerlo sobre un corpus ya algo mas rico

## Primeros pasos exactos para la proxima sesion

1. Verificar rapido que `main` esta limpio y alineado:

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
```

2. Revisar el plan maestro y la tabla canónica:

```bash
docs/regulatory-compliance-expansion-plan.md
```

3. Identificar las siguientes obligaciones candidatas de mayor valor:

- `Circular 1/2010`
- `Circular 4/2018`
- `Ley 10/2010`
- `RD 304/2014`

4. Sembrar nuevas obligaciones en tests antes de automatizar derivacion.

5. Extender `GET /v1/obligaciones` y `GET /v1/obligaciones/{codigo}` con ese nuevo set.

6. Solo despues valorar si merece la pena introducir ya:

- `documento_fragmento`
- `documento_seccion`

## Archivos clave para retomar

- `docs/regulatory-compliance-expansion-plan.md`
- `apps/workers/cnmv.py`
- `apps/workers/sepblac.py`
- `apps/workers/boe.py`
- `apps/api/routers/cnmv.py`
- `apps/api/routers/sepblac.py`
- `apps/api/routers/obligaciones.py`
- `apps/api/schemas.py`
- `apps/api/tests/conftest.py`
- `apps/api/tests/test_smoke.py`
- `alembic/versions/20260416_0001_baseline_schema.py`

## Nota final

La proxima sesion no necesita reabrir el debate de si `CNMV` y `SEPBLAC` deben existir o como encajan.

Eso ya esta hecho.

El punto de partida correcto ya es este:

- plan regulatorio documentado
- corpus inicial canonizado
- `CNMV` implementado
- `SEPBLAC` implementado
- `obligacion_regulatoria` implementada en su primer slice
- `main` limpio y sincronizado con `origin/main`

# Regulatory Compliance Expansion Plan

## Goal

- Diseñar la siguiente expansión regulatoria de `esdata` para cubrir un bloque de compliance operativo que combine `CNMV`, `SEPBLAC`, `BOE` y `UE`.
- Preparar una arquitectura que no solo indexe documentos, sino que permita normalizar obligaciones, estados, formularios, secciones y trazabilidad regulatoria.
- Dejar una base compatible con el patrón actual del repo: workers por fuente, routers específicos y una capa común reutilizable para reglas y reporting.

## Assumptions / constraints

- Este documento cierra la fase de planificación y deja el trabajo listo para ejecutarse después.
- El diseño debe encajar con la arquitectura actual de `esdata`, que ya separa fuentes documentales y normativas por worker y router.
- El alcance acordado incluye `CNMV`, `SEPBLAC`, `BOE` y `UE`.
- La meta funcional no es solo un corpus consultable: el objetivo es llegar a una capa de compliance operativo normalizada a nivel de obligación.
- Las referencias dudosas del corpus inicial se han validado durante la sesión y quedan reflejadas aquí como canon definitivo o como notas de confirmación posterior.

## Research (current state)

### Modules/subprojects involved

- `apps/workers/`
- `apps/api/routers/`
- `apps/api/schemas.py`
- `apps/api/tests/`
- `alembic/`
- `docs/`
- `scripts/smoke-check.py`

### Key files/paths

- `apps/workers/boe.py`
- `apps/workers/bdns.py`
- `apps/workers/borme.py`
- `apps/api/routers/bdns.py`
- `apps/api/routers/borme.py`
- `apps/api/routers/empresas.py`
- `apps/api/main.py`
- `alembic/versions/20260416_0001_baseline_schema.py`
- `README.md`
- `docs/architecture.md`

### Entrypoints (API/UI/CLI/Jobs)

- Workers por fuente: `boe`, `dgt`, `teac`, `modelos`, `bdns`, `borme`
- Routers FastAPI por dominio/fuente
- Smoke checks HTTP vía `scripts/smoke-check.py`

### Related configs/flags

- Variables de entorno por worker en `.env.example`
- `docker-compose.yml`
- `infra/deploy/docker-compose.prod.yml`
- `.github/workflows/deploy.yml`

### Data models/storage touched

- `norma`
- `documento_interpretativo`
- `empresa`
- `documento_empresa`
- falta una capa de `obligacion_regulatoria`

### Interfaces/contracts (APIs/events/IPC)

- REST API pública en FastAPI
- Workers de ingesta con persistencia en Postgres y compatibilidad con SQLite en tests

### Existing patterns to follow

- Nuevas fuentes documentales se modelan con worker propio + router propio
- La normativa jerárquica reutiliza `norma`
- Las fuentes documentales reutilizan `documento_interpretativo`
- Las relaciones nuevas se expresan con tablas puente

## Analysis

### Options

1. Modelar todo como una sola “fuente CNMV”
   - Ventaja: arranque rápido
   - Inconveniente: mezcla `CNMV`, `SEPBLAC`, `BOE` y `UE` y rompe la trazabilidad entre norma, circular, manual y formulario

2. Separar por fuente y unificar mediante una capa común de obligaciones
   - Ventaja: encaja con el patrón actual del repo y escala mejor
   - Inconveniente: obliga a diseñar taxonomía y relaciones antes de codificar

3. Empezar directamente por obligaciones sin corpus documental limpio
   - Ventaja: acerca antes al objetivo funcional final
   - Inconveniente: alto riesgo de modelado incorrecto por falta de canonización previa

### Decision

- Chosen: opción 2
- Why:
  - `esdata` ya funciona mejor cuando cada fuente tiene su propio worker y su propia superficie API
  - `CNMV`, `SEPBLAC`, `BOE` y `UE` tienen naturalezas distintas y no conviene colapsarlas en una sola fuente
  - la capa común correcta no es la fuente, sino una entidad nueva de `obligacion_regulatoria`

### Risks / edge cases

- Documentos derogados o históricos mezclados con normativa vigente
- Distinguir correctamente entre norma, circular, manual, formulario y estado
- Secciones, anexos y disposiciones adicionales con referencias internas complejas
- Los formularios SEPBLAC no son equivalentes a normas ni a doctrina
- Algunos estados reservados o estadísticos pueden requerir taxonomía propia
- Las fuentes públicas pueden tener acceso web heterogéneo o con HTML poco estable

### Open questions

- No quedan preguntas bloqueantes para el plan
- La implementación necesitará una canonización fina de cada referencia exacta antes de comenzar la fase técnica

## Q&A results (captured after the session)

### Outcome/acceptance criteria

- Dejar un plan maestro accionable y versionado en el repo
- Separar correctamente `CNMV`, `SEPBLAC`, `BOE` y `UE`
- Diseñar una expansión orientada a compliance operativo, no solo a indexación documental

### Scope boundaries

- Primera ola de diseño: `CNMV`, `SEPBLAC`, `BOE`, `UE`
- Fuera de esta fase: implementación completa del corpus y extracción final de obligaciones

### Constraints/non-goals

- No mezclar este bloque nuevo con la capa fiscal AEAT ya operativa
- No tratar documentos operativos como si fueran normativa jerárquica cuando no lo son

### Decisions made in Q&A

- `RD 304/2014`, no `304/2017`
- `Reglamento Delegado (UE) 2017/584`
- `Ley 35/2003`, no `25/2003`
- `Circular 5/2016` CNMV, tratada como histórica/derogada
- `Circular 1/2010` para la referencia abreviada
- `Sección 15.5 SEPBLAC` ligada a `Ley 10/2010, de 28 de abril`
- `Modelo 19 SEPBLAC` tratado como formulario oficial de comunicación de operativa sospechosa por indicio

### Remaining open questions (if any)

- Ninguna bloqueante para el plan

## Canonical corpus (initial wave)

### UE / EUR-Lex

1. `Reglamento (UE) 2019/2033`
2. `Reglamento Delegado (UE) 2017/584`

### BOE

3. `Real Decreto 304/2014`
4. `Real Decreto 848/2001, de 3 de agosto`
5. `Real Decreto 1082/2012, de 13 de julio`
6. `Ley 10/2010, de 28 de abril`
7. `Ley 35/2003`
8. `Reglamento de desarrollo de la Ley 35/2003` si finalmente entra en el corpus de la primera ola

### CNMV

9. `Circular 9/2008`
10. `Circular 6/2011`
11. `Circular 5/2016` como histórica
12. `Circular 1/2010`
13. `Circular 3/2014`
14. `Circular 4/2018`
15. `Circular 1/2015`

### SEPBLAC

16. `Modelo 19 SEPBLAC`
17. `Manual de procedimiento para la prevención del blanqueo de capitales y de la financiación del terrorismo`
18. Referencias operativas ligadas a la `Sección 15.5` en el marco de `Ley 10/2010`

## Data model proposal

### Reuse existing models

- `norma`
  - reglamentos UE
  - reales decretos y leyes BOE
- `documento_interpretativo`
  - circulares CNMV
  - manuales SEPBLAC
  - formularios SEPBLAC
  - guías e instrucciones operativas

### Add new models

- `obligacion_regulatoria`
- `obligacion_documento`
- Opcional en fase posterior: `documento_fragmento` o `documento_seccion`

### Minimum fields for `obligacion_regulatoria`

- `id`
- `codigo`
- `nombre`
- `fuente`
- `organismo_emisor`
- `tipo_obligacion`
- `sujeto_obligado`
- `periodicidad`
- `reporte_modelo`
- `ambito`
- `estado_vigencia`
- `documento_origen_tipo`
- `documento_origen_ref`
- `seccion_origen`
- `anexo_origen`
- `nota`

## Implementation plan

1. Crear una tabla maestra canónica del corpus regulatorio.
2. Clasificar cada referencia por fuente, tipo, vigencia, prioridad y tratamiento técnico.
3. Diseñar una taxonomía común para `tipo_fuente`, `organismo_emisor`, `ambito`, `tipo_documento` y `tipo_obligacion`.
4. Implementar `worker-cnmv`.
5. Implementar `worker-sepblac`.
6. Implementar soporte UE adicional con un nuevo `worker-eurlex` o una extensión reutilizable del patrón actual.
7. Reutilizar `worker-boe` para la capa BOE española de este corpus.
8. Añadir nuevas rutas: `/v1/cnmv`, `/v1/sepblac`, `/v1/obligaciones`.
9. Añadir migración para `obligacion_regulatoria` y `obligacion_documento`.
10. Implementar troceado selectivo de secciones, anexos, disposiciones adicionales y formularios.
11. Normalizar obligaciones derivadas.
12. Enlazar obligación -> documento -> norma superior.
13. Extender smoke checks.
14. Añadir tests unitarios e integración por fuente.
15. Actualizar docs y cobertura visible del producto.

## Phases

### Fase 0

Inventario maestro y canonización.

Entregable:

- tabla completa validada por fuente, tipo y vigencia

### Fase 1

Capa documental regulatoria.

Entregable:

- corpus consultable por fuente

### Fase 2

Troceado operativo.

Entregable:

- navegación por secciones, anexos, disposiciones y formularios

### Fase 3

Obligaciones normalizadas.

Entregable:

- `/v1/obligaciones`

### Fase 4

Enlaces cruzados y trazabilidad.

Entregable:

- obligación -> documento -> norma -> empresa cuando aplique

## Recommended priority

1. `Reglamento (UE) 2019/2033`
2. `Ley 10/2010`
3. `Real Decreto 304/2014`
4. `Circular 9/2008`
5. `Circular 6/2011`
6. `Circular 1/2010`
7. `Circular 3/2014`
8. `Circular 4/2018`
9. `Circular 1/2015`
10. `Modelo 19 SEPBLAC`
11. `Manual PBC/FT`
12. `Real Decreto 848/2001`
13. `Real Decreto 1082/2012`
14. `Reglamento Delegado (UE) 2017/584`
15. `Circular 5/2016` como histórica

## Tests to run

- `ruff` sobre workers, routers, schemas y tests nuevos
- `pytest` en:
  - `apps/api/tests/`
  - `apps/workers/tests/test_cnmv.py`
  - `apps/workers/tests/test_sepblac.py`
  - `apps/workers/tests/test_eurlex.py`
- `scripts/smoke-check.py`
- validación de `/status` para nuevos workers

## Definition of done

Este bloque regulatorio estará bien encaminado cuando exista:

- corpus validado por fuente
- documentos clave accesibles por API
- obligaciones normalizadas mínimas
- trazabilidad a sección/anexo/documento
- smoke tests nuevos
- documentación de arquitectura actualizada

# [REFERENCE] Regulatory Compliance Expansion Plan

> Este documento queda como referencia conceptual del bloque compliance/regulatorio. La fuente activa unica de estado y ejecucion es `docs/master-execution-roadmap.md`.

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

## Fase 0 deliverable: master inventory

La Fase 0 queda materializada en esta tabla maestra. Su objetivo es dejar cada referencia clasificada por fuente, tipo, prioridad, tratamiento técnico y estado de validación antes de empezar la implementación.

| Referencia original | Referencia canónica | Fuente | Tipo | Vigencia | Prioridad | Fase objetivo | Tratamiento técnico | Estado validación | Notas |
|---|---|---|---|---|---|---|---|---|---|
| Reglamento de solvencia 2019/2033 | Reglamento (UE) 2019/2033 | UE / EUR-Lex | reglamento_ue | vigente | alta | Fase 1-3 | `norma` | validada | Base prudencial de referencia |
| Reglamento delegado 217/584 | Reglamento Delegado (UE) 2017/584 | UE / EUR-Lex | reglamento_delegado_ue | vigente | media | Fase 1-3 | `norma` | validada | Pendiente de mapear su relación exacta con reporting/operativa del corpus |
| Estados financieros Circular 9/2008 | Circular 9/2008, de 10 de diciembre, de la CNMV | CNMV | circular | vigente modificada | alta | Fase 1-3 | `documento_interpretativo` + obligaciones derivadas | parcialmente validada | BOE identificado vía `BOE-A-2009-133` en búsqueda; base contable y estados públicos/reservados |
| Circular 6/2011 | Circular 6/2011, de 12 de diciembre, de la CNMV | CNMV | circular_modificadora | vigente modificada | alta | Fase 1-3 | `documento_interpretativo` + enlace a circular base | parcialmente validada | Modifica la Circular 9/2008 |
| Circular 5/2016m | Circular 5/2016, de la CNMV | CNMV | circular_modificadora | derogada/histórica | baja | Fase 1-2 | `documento_interpretativo` histórico | validada con nota | Mantener como referencia histórica, no como base viva |
| Circular 1/2010 | Circular 1/2010, de 28 de julio, de la CNMV | CNMV | circular | vigente modificada | alta | Fase 1-3 | `documento_interpretativo` + obligaciones derivadas | validada | Información reservada de entidades que prestan servicios de inversión |
| Circular 3/2014 | Circular 3/2014, de 22 de octubre, de la CNMV | CNMV | circular_modificadora | vigente histórica | media | Fase 1-3 | `documento_interpretativo` + enlace a Circular 1/2010 | validada | BOE localizado como `BOE-A-2014-11497` |
| Circular 4/2018 | Circular 4/2018, de 27 de septiembre, de la CNMV | CNMV | circular_modificadora | vigente | alta | Fase 1-3 | `documento_interpretativo` + enlace a Circulares 1/2010 y 7/2008 | validada | BOE localizado como `BOE-A-2018-13716` |
| Información estadística infraestructuras de mercado Circular 1/2015 | Circular 1/2015, de 23 de junio, de la CNMV | CNMV | circular | vigente modificada | media | Fase 1-3 | `documento_interpretativo` + obligaciones derivadas | validada | BOE localizado como `BOE-A-2015-7185` |
| Circular 1/2010 disp. adic. segunda | Disposición adicional segunda de la Circular 1/2010 | CNMV | fragmento_normativo | vigente según texto consolidado | media | Fase 2-3 | `documento_fragmento` o troceado de documento | validada funcionalmente | No conviene modelarla como documento independiente |
| Modelo SEPBLAC 19 | Modelo 19 SEPBLAC de comunicación por indicio | SEPBLAC | formulario_oficial | vigente por confirmar en fase técnica | alta | Fase 1-3 | `documento_interpretativo` + `obligacion_regulatoria` | validada funcionalmente | Tratar como formulario oficial operativo, no como norma |
| Real Decreto 304/2017 | Real Decreto 304/2014 | BOE | real_decreto | vigente modificada | alta | Fase 1-3 | `norma` | validada | Reglamento PBC/FT asociado a Ley 10/2010 |
| Sección 15.5 SEPBLAC | Sección 15.5 vinculada al marco de la Ley 10/2010 | SEPBLAC | seccion_operativa | vigente por confirmar | alta | Fase 2-3 | `documento_fragmento` o troceado de manual | validada funcionalmente | No es una norma separada; debe ligarse al documento operativo fuente |
| Ley 10/2010 de 28 de abril | Ley 10/2010, de 28 de abril | BOE | ley | vigente | alta | Fase 1-3 | `norma` | validada | Base legal del bloque PBC/FT |
| Real Decreto 848/2001 de 3 de agosto | Real Decreto 848/2001, de 3 de agosto | BOE | real_decreto | vigente o histórica a confirmar | media | Fase 1-2 | `norma` | validada funcionalmente | Requiere verificación fina de ámbito exacto en Fase 1 |
| Manual de procedimiento para la prevención del blanqueo de capitales y financiación del terrorismo | Manual PBC/FT | SEPBLAC | manual_operativo | vigente por confirmar | alta | Fase 1-3 | `documento_interpretativo` + troceado posterior | validada funcionalmente | Documento operativo clave para derivar procedimientos y formularios |
| Real Decreto 1082/2012 de 13 de julio | Real Decreto 1082/2012, de 13 de julio | BOE | real_decreto | vigente o histórica a confirmar | media | Fase 1-2 | `norma` | validada funcionalmente | Verificar alcance exacto en el corpus regulatorio final |
| Reglamento de desarrollo de la Ley 25/2003 | Reglamento de desarrollo de la Ley 35/2003 | BOE | reglamento_desarrollo | vigente por confirmar | media | Fase 1-2 | `norma` | validada con corrección | Confirmar referencia BOE exacta en el arranque técnico |

### Estado de cierre de la Fase 0

- El corpus ya está separado por fuente (`UE`, `BOE`, `CNMV`, `SEPBLAC`).
- Las referencias ambiguas de la sesión ya están corregidas o marcadas como validación funcional pendiente de identificación fina en la implementación.
- La tabla anterior es suficiente para arrancar la Fase 1 sin volver a rediscutir el alcance conceptual.

## Estado de Fase 1: Capa documental regulatoria

- Manifest de ejecucion recomendado para la siguiente ola: `docs/source-manifests/sociedad-valores-wave-1.md`

### Entregables completados

- **CNMV**: worker `cnmv.py` implementado, router `/v1/cnmv` expuesto, endpoints `listar_cnmv` y `get_cnmv` en MCP
- **SEPBLAC**: worker `sepblac.py` implementado, router `/v1/sepblac` expuesto, endpoints `listar_sepblac` y `get_sepblac` en MCP
- **Empresas**: tabla `empresa` y `documento_empresa` implementadas, router `/v1/empresas` expuesto
- **BORME**: ingesta de actos societarios implementada, router `/v1/borme` expuesto, endpoints `listar_borme` y `get_borme` en MCP
- **BDNS**: ingesta de convocatorias de subvenciones implementada, router `/v1/bdns` expuesto, endpoints `listar_bdns` y `get_bdns` en MCP
- **Obligaciones**: tabla `obligacion_regulatoria` y `obligacion_documento` implementadas, router `/v1/obligaciones` expuesto, endpoints `listar_obligaciones` y `get_obligacion` en MCP

### MCP - Superficie de consulta unificada

Se implementó el servidor MCP con 36 operaciones que unifican el acceso a todas las fuentes:

| Fuentes | Estado | Operaciones MCP |
|---|---|---|
| Legislacion BOE | ✅ Completo | 7 operaciones |
| Materias | ✅ Completo | 2 operaciones |
| Doctrina DGT/TEAC | ✅ Completo | 2 operaciones |
| Modelos AEAT (25 modelos) | ✅ Completo | 12 operaciones |
| Consulta fiscal inteligente | ✅ Completo | 1 operación principal |
| BORME (Registro Mercantil) | ✅ Fase 1 | 2 operaciones |
| SEPBLAC (Blanqueo capitales) | ✅ Fase 1 | 2 operaciones |
| Empresas (capa societaria) | ✅ Fase 1 | 2 operaciones |
| Obligaciones regulatorias | ✅ Fase 1 | 2 operaciones |
| BDNS (Subvenciones) | ✅ Fase 1 | 2 operaciones |
| CNMV (Mercado valores) | ✅ Fase 1 | 2 operaciones |
| **Total** | | **36 operaciones** |

### Consulta fiscal inteligente

El endpoint `/v1/consulta` permite consultas en lenguaje natural que cruzan todas las fuentes:

- Legislacion vigente con enlazado a articulos
- Doctrina DGT y TEAC vinculada a normas
- Modelos AEAT con casillas, claves e instrucciones
- Datos internacionales (convenios DT, CRS, FATCA, DAC, W-8)
- Fallback ILIKE para terminos en inglés (FATCA, CRS, W-8BEN, GIIN, DAC, BEPS, OECD)
- Clarificacion de terminologia AEAT (FactA ≠ Facturae)

### Datos internacionales

Adicionalmente se ingesto cobertura internacional completa:

- 166 normas internacionales
- 107 convenios de doble tributacion (ES-XX) con textos estructurados por articulo
- 60 paises con informacion TIN/NRF
- 10 normas informativas (CRS/OECD, FATCA, DAC1-DAC11)
- Formularios W-8 (W-8BEN, W-8BEN-E, GIIN, FFI, NFFE)
- Normativa UE (NIF/NRF, VIES, OSS, ROIR)
- 4371 articulos totales en la base de datos

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

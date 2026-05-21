# PRD: DGT y TEAC como lineas de criterio fiscal

## Objetivo

Crear una familia fiscal propia para doctrina administrativa, separada de AEAT modelos, CDI y jurisprudencia judicial, que permita consultar criterios por impuesto, articulo, modelo, tema y fuente oficial.

El resultado esperado no es afirmar que toda la doctrina fiscal espanola esta resuelta. El objetivo es convertir resoluciones DGT y TEAC en lineas de criterio utilizables cuando exista evidencia trazable, y devolver `safe_to_answer=false` cuando falte base suficiente.

## Contexto

El repo ya contiene piezas operativas relevantes:

- Corpus DGT/TEAC en `documento_interpretativo`.
- Workers `apps/workers/dgt.py`, `apps/workers/dgt_doctrina.py` y TEAC.
- Busqueda y detalle en `apps/api/routers/doctrina.py`.
- Capa editorial `linea_criterio` y `linea_criterio_referencia`.
- Curacion semiasistida en `apps/api/routers/criterio_curacion.py`.
- Nueva superficie read-only `/v1/doctrina/lineas` para exponer lineas con evidencia/fail-closed.

La lectura correcta es `implemented_partial`: hay corpus, busqueda, detalle, lineas editoriales y contrato inicial de cobertura, pero falta normalizar cada linea por impuesto, articulo, tema, modelo y fuente oficial antes de tratarla como producto doctrinal completo.

## No Objetivos

- No cargar toda la jurisprudencia tributaria.
- No resolver litigiosidad judicial.
- No sustituir texto oficial por inferencia LLM.
- No mezclar doctrina administrativa con AEAT modelos.
- No calcular retenciones ni aplicabilidad completa sin criterio oficial trazable.
- No prometer cobertura total de todas las resoluciones.
- No usar resumen LLM como fuente de verdad.
- No redisenar la arquitectura global del repo.

## Estados Permitidos

Por linea, tema o fuente usar solo:

- `complete`
- `partial`
- `target`
- `configured_but_unavailable`
- `out_of_scope`

DGT/TEAC como familia no puede pasar a `complete` hasta que exista un lote declarado que cumpla la definicion de hecho completa.

## Definicion De Hecho

Una linea de criterio solo puede quedar `complete` si cumple todo esto:

1. Fuente oficial identificada.
2. Resolucion o consulta trazable.
3. Texto o ficha oficial cargada con `source_url`, `capture_date` y hash o equivalente.
4. Clasificacion por impuesto, articulo, tema y, cuando aplique, modelo.
5. Estado vigente o relacion historica explicita.
6. API o MCP expone la consulta.
7. Tests de contrato cubren encontrado, no encontrado y evidencia parcial.
8. Respuesta `fail-closed` cuando falte base suficiente.

Si falla uno de estos puntos, la linea no puede marcarse `complete`.

## Alcance Inicial

### Fuentes doctrinales

- DGT.
- TEAC.

### Temas prioritarios

| Tema | Hipotesis inicial | Motivo | Accion inicial |
| --- | --- | --- | --- |
| Retenciones no residentes | `target` | Relaciona DGT/TEAC, IRNR, CDI y modelos; alto riesgo de sobreafirmar | Identificar consultas/resoluciones oficiales por articulo y tipo de renta |
| IVA intracomunitario | `target` | Frecuente y conectado con modelos 303/349 | Curar lineas por LIVA, operaciones y modelo relacionado |
| Operaciones vinculadas | `target` | Requiere separar doctrina, norma y modelos informativos | Mapear por LIS/RIS y modelos 200/232 cuando aplique |
| CRS/FATCA | `target` | Tiene contacto con modelos 289/290, pero la doctrina no es el formulario | Curar solo criterios con fuente DGT/TEAC trazable |
| Criptoactivos | `target` | Alto riesgo de inferencia fuera de corpus | Exigir fuente doctrinal oficial y fecha |
| Dividendos, intereses y canones | `target` | Relaciona IRNR/CDI/modelos | Separar criterio doctrinal de calculo de retencion |
| Establecimiento permanente | `target` | Necesita articulo, caso y fuente | Curar DGT/TEAC por supuesto |
| Servicios profesionales | `target` | Frecuente en IRPF/IVA/IRNR | Mapear por impuesto y articulo |
| Aplicabilidad a modelos AEAT | `partial` | Existen enlaces indirectos por articulo/modelo, pero no contrato doctrinal cerrado | Marcar como inferido salvo relacion trazable |

## Modelo De Datos Objetivo

No es obligatorio crear estas tablas con estos nombres exactos, pero el contrato debe cubrir estos conceptos.

| Entidad | Campos minimos |
| --- | --- |
| `linea_criterio` | `id`, `fuente`, `codigo`, `titulo`, `tema`, `impuesto`, `articulo_referencia`, `modelo_aeat_referencia`, `fecha`, `estado_vigente`, `resumen_oficial`, `source_url`, `source_hash`, `capture_date`, `verified`, `completeness` |
| `criterio_relacion` | `linea_criterio_id`, `norma_codigo`, `articulo`, `modelo_aeat`, `tipo_renta`, `relacion`, `nota_limitacion` |
| `criterio_tema` | `linea_criterio_id`, `tema`, `palabras_clave`, `prioridad`, `vigente` |

La estructura actual reutiliza `linea_criterio`, `linea_criterio_referencia`, `documento_interpretativo` y `documento_articulo`. Esto es suficiente para un contrato parcial, pero no para marcar lineas `complete` sin campos normalizados de impuesto/modelo/tipo de supuesto.

## Contrato API/MCP

### API minima

- `GET /v1/doctrina/lineas`
- `GET /v1/doctrina/lineas/{codigo}`
- `GET /v1/doctrina/lineas?impuesto=&tema=&modelo=`
- `GET /v1/doctrina/lineas/{codigo}/relaciones`
- `GET /v1/doctrina/lineas/coverage`

### API legacy relacionada

- `GET /v1/doctrina/buscar`
- `GET /v1/doctrina/{referencia}`
- `GET /v1/criterio`
- `GET /v1/criterio/{linea_id}`
- `GET /v1/criterio/curacion/suggest`
- `POST /v1/criterio/curacion/assign`

### MCP minimo

- `listar_lineas_criterio`
- `detalle_linea_criterio`
- `buscar_lineas_criterio`
- `criterio_relacionado_con_modelo`
- `doctrina_coverage`

Cada respuesta factual debe incluir:

- `verified`
- `completeness`
- `source_url`
- `capture_date` o equivalente
- `safe_to_answer`
- `evidence_notice`
- `review_required`

## Reglas Fail-Closed

El sistema debe abstenerse o marcar `safe_to_answer=false` cuando:

- el criterio no existe en el corpus cargado,
- el texto oficial no esta cargado,
- falta relacion con articulo o impuesto,
- la relacion con modelo AEAT es inferida y no trazable,
- la fuente oficial no tiene URL o fecha de captura trazable,
- el dato procede de resumen o seed historico sin evidencia suficiente.

No se debe presentar una interpretacion como si fuera doctrina oficial cerrada.

## Revision De Coherencia 2026-05-21

| Superficie | Estado coherente | Motivo |
| --- | --- | --- |
| `documento_interpretativo` DGT/TEAC | `implemented_partial` | Hay corpus y busqueda, pero la cobertura depende de discovery y completitud por fila |
| `linea_criterio` | `implemented_partial` | Existe capa editorial, pero no clasifica sistematicamente impuesto/articulo/modelo/tema |
| `/v1/doctrina/lineas` | `implemented_partial` | Expone contrato de evidencia y abstencion segura sobre la estructura actual |
| `/v1/criterio/curacion/*` | `partial` | Ayuda a asignar documentos, pero no valida juridicamente la linea |
| MCP HTTP | `implemented_partial` | Expone herramientas de lineas/coverage, pero no convierte lineas parciales en completas |

Regla de coherencia: "documento cargado", "linea consultable" y "criterio utilizable para responder" son estados distintos.

## Auditoria Produccion 2026-05-21

Informe vivo: `docs/doctrina-production-audit-20260521.md`.

Hallazgos principales contra VPS `steamcases-vps`, con contrato doctrinal desplegado el 2026-05-21:

| Superficie | Resultado productivo | Estado |
| --- | --- | --- |
| DGT `consulta_vinculante` | `18.631` consultas; `18.621 complete`, `10 partial`; todas con URL PETETE y texto | `implemented_partial` |
| TEAC `resolucion_teac` | `558` resoluciones; `290 complete`, `268 partial`; todas con URL DYCTEA, `552` con texto | `implemented_partial` |
| `source_revision` | SHA-256 para `18.631` DGT y `558` TEAC, pero no proyectado directamente en `documento_interpretativo` | `partial` |
| `linea_criterio` | `7` lineas activas editoriales; ninguna referencia DGT/TEAC resuelve a documento oficial cargado | `target` para doctrina fiscal |
| `/v1/doctrina/lineas/coverage` en produccion | HTTP 200; `estado=implemented_partial`, `lineas_total=16`, `lineas_complete=1`, `safe_to_answer=false` | `implemented_partial` |

Lote piloto seleccionado para curacion. Tras el cierre D-01, una linea queda `complete`; el resto sigue `partial`:

| Linea piloto | Referencias productivas iniciales | Estado |
| --- | --- | --- |
| Retenciones no residentes | DGT `V0166-25`; TEAC `00/02188/2017/00/00` como soporte parcial | `complete` |
| IVA intracomunitario | DGT `V0236-26`; TEAC `00/02766/2015/00/00` | `partial` |
| Operaciones vinculadas | DGT `V0144-26`; TEAC `00/06460/2019/00/00` | `partial` |
| CRS/FATCA | DGT `V0138-24` | `partial` |
| Criptoactivos | DGT `V0162-26` | `partial` |
| Dividendos/intereses | DGT `V0187-26`; TEAC `00/02188/2017/00/00` o `00/00185/2017/00/00` | `partial` |
| Canones | DGT `V0228-26` | `partial` |
| Establecimiento permanente | DGT `V0235-26`; TEAC `00/03519/2022/00/00` | `partial` |
| Servicios profesionales | DGT `V0191-26` | `partial` |

Regla de cierre: D-01 queda `complete` porque cumple el contrato completo; ninguna otra linea queda `complete` hasta crear o endurecer el contrato de linea con impuesto, articulo, tema, modelo cuando aplique, estado vigente/historico y proyeccion de `source_hash`/`capture_date`.

Regla D-01: si el documento pertenece a otro marco normativo distinto de IRNR, no se fuerza a retenciones no residentes aunque tenga fuente, hash y texto completo. `V0223-26` queda descartada como principal D-01 por este motivo. `V0166-25` queda como consulta principal completa porque cita TRLIRNR art. 31 y modelos 216/296, tiene hash/captura, enlace persistido `manual_official`, vigencia historica explicita y modelo auditado por curacion del supuesto. La relacion de modelo queda pendiente de una relacion persistida especifica; la curacion auditada no debe presentarse como tabla relacional cerrada.

## Curacion Local Lote Piloto 2026-05-21

El contrato local expone ahora las nueve lineas piloto como codigos estables `D-01` a `D-09`:

| Codigo | Tema | Impuesto | Modelo relacionado | Estado contractual |
| --- | --- | --- | --- | --- |
| `D-01` | Retenciones no residentes | IRNR | 216/296 | `complete` con DGT `V0166-25`; TRLIRNR art. 31 persistido, vigencia historica explicita y modelo auditado por curacion del supuesto, pendiente de relacion persistida especifica |
| `D-02` | IVA intracomunitario | IVA | 349 | `partial`; `V0236-26` no se usa como cierre porque trata tipo impositivo/LIVA 91, no supuesto intracomunitario expreso |
| `D-03` | Operaciones vinculadas | IS | 232 | `partial`; `V0144-26` permite `LIS art. 18`, pero no modelo 232 ni vigencia cerrada |
| `D-04` | CRS/FATCA | Informacion fiscal | 289 | `partial`; modelo 289 trazable en `V0138-24`, pero falta articulo/supuesto normalizado y vigencia |
| `D-05` | Criptoactivos | IRPF | 721 | `partial`; hay monedas virtuales, pero no modelo 721 ni articulo operativo suficiente |
| `D-06` | Dividendos e intereses | IRNR | 216 | `partial`; dividendos IRNR trazables, pero falta separar intereses, persistir articulo y validar modelo |
| `D-07` | Canones | IRNR | 216 | `partial`; `V0228-26` no cierra canon IRNR, solo LIVA/servicios |
| `D-08` | Establecimiento permanente | IRNR | 200 | `partial`; depende de hechos/convenio y no hay modelo 200 trazable |
| `D-09` | Servicios profesionales | IRNR | 216 | `partial`; `V0191-26` es LIVA art. 20, no cierre IRNR de servicios profesionales |

Reglas aplicadas:

- Las lineas piloto se resuelven contra `documento_interpretativo`, `source_revision` y `documento_articulo`; no usan resumen LLM como evidencia.
- `source_hash` y `capture_date` proceden de `source_revision` cuando existe.
- La relacion con modelo AEAT solo se expone cuando hay evidencia documental auditada. En D-01 la relacion 216/296 queda auditada por curacion del supuesto, pendiente de relacion persistida especifica; D-04 conserva 289 como evidencia parcial; D-02, D-03, D-05, D-06, D-07, D-08 y D-09 no exponen modelo por conocimiento general.
- `lineas_complete` permanece en `1` por D-01. La familia completa sigue `implemented_partial` porque D-02 a D-09 no cumplen todavia los ocho puntos del criterio de hecho.

## Tareas

1. Auditar el estado real de DGT y TEAC en produccion.
2. Confirmar que corpus ya esta cargado y cual sigue parcial.
3. Endurecer la familia `linea_criterio` o crear tablas doctrinales si la estructura actual no basta.
4. Definir el lote piloto de temas prioritarios.
5. Implementar o endurecer ingesta por resolucion/consulta.
6. Exponer cobertura por tema, impuesto y modelo relacionado.
7. Endurecer API/MCP con evidencia y abstencion segura.
8. Crear tests de contrato para encontrado, parcial, no encontrado y falta de evidencia.
9. Actualizar la matriz fiscal-regulatoria.
10. Documentar gaps por tema y siguiente accion.

## Criterios De Aceptacion

1. DGT y TEAC aparecen como familia propia, no como apendice generico.
2. La matriz clasifica doctrina como `implemented_partial` hasta cerrar el contrato.
3. Existe inventario de lineas de criterio por tema.
4. Cada respuesta declara evidencia y completitud.
5. El sistema no inventa doctrina ni interpreta como hecho lo que no esta trazado.
6. Los tests fallan si una respuesta factual no incluye evidencia.
7. Los gaps quedan documentados por tema y linea.
8. El contrato permite responder si una linea es utilizable o solo consultable parcialmente.

## Entregables

- `docs/doctrina-coverage-prd.md`
- Inventario inicial de lineas de criterio por tema.
- Contrato de cobertura doctrinal.
- API/MCP endurecido.
- Tests de contrato.
- Actualizacion de `docs/fiscal-regulatory-coverage-matrix.md`.
- Actualizacion del roadmap si cambia el estado visible.

## Resultado Esperado

La respuesta correcta a "DGT/TEAC estan hechos?" debe ser:

> DGT y TEAC existen como superficie parcial: hay corpus, respuestas y base operativa, pero no estan cerrados como producto doctrinal completo hasta normalizar lineas de criterio, mapear temas y hacer que API/MCP respondan con evidencia y abstencion segura.

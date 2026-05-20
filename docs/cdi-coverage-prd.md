# PRD: CDI coverage and ingestion contract

## Objetivo

Cerrar la familia de Convenios de Doble Imposicion (CDI/DTA) como producto fiscal propio, separada de AEAT modelos, IRNR, FATCA/CRS e IRS.

El resultado debe permitir consultar convenios por pais, articulo y tipo de renta con evidencia oficial, estado de cobertura y comportamiento `fail-closed` cuando falte base suficiente.

## Contexto

El cierre AEAT prioritario ya dejo claro que AEAT no debe tratarse como un bloque unico. CDI queda fuera de ese cierre porque no es un modelo domestico, sino una familia internacional con fuentes, estructura y riesgos propios.

El repo ya contiene piezas operativas relevantes:

- Worker `apps/workers/cdi.py`, con fuentes AEAT/Hacienda y cadencia semanal.
- Router `apps/api/routers/dta_convenios.py`, bajo `/v1/internacional/convenios`.
- Tools MCP para listar convenios, consultar detalle y calcular retencion.
- Tests `apps/api/tests/test_dta_convenios.py` y `apps/workers/tests/test_cdi.py`.
- Evidencia historica de VPS con 86 convenios CDI cargados.

Este PRD no marca CDI como `complete`. La lectura correcta es `implemented_partial`: hay worker, datos y superficie API/MCP, pero falta contrato de producto por pais, articulo, tipo de renta, evidencia y abstencion segura.

## No Objetivos

- No resolver fiscalidad internacional completa en este PRD.
- No prometer todos los paises en el primer lote.
- No mezclar CDI con AEAT modelos 210, 216, 296, 289 o 290.
- No usar IRS DTA como fuente autoritativa para convenios firmados por Espana.
- No calcular retenciones como respuesta final si no hay articulo, protocolo y fuente oficial trazable.
- No usar texto LLM como corpus ni como evidencia.
- No cargar datos nuevos sin contrato, tests y trazabilidad.

## Fuentes Oficiales

Fuentes primarias iniciales:

- AEAT CDI: `https://sede.agenciatributaria.gob.es/Sede/normativa-criterios-interpretativos/fiscalidad-internacional/convenios-doble-imposicion-firmados-espana.html`
- Hacienda CDI: `https://www.hacienda.gob.es/es-ES/Normativa%20y%20doctrina/Normativa/CDI/Paginas/CDI_Alfa.aspx`
- BOE, cuando el convenio, protocolo, instrumento de ratificacion o correccion tenga referencia oficial.

Regla: si hay conflicto entre fuente agregada y BOE oficial del convenio/protocolo, el dato queda `partial` hasta resolver la referencia.

## Estados Permitidos

Por convenio, articulo y tipo de renta usar solo:

- `complete`
- `partial`
- `target`
- `configured_but_unavailable`
- `out_of_scope`

CDI como familia solo puede pasar a `complete` si el lote declarado cumple el criterio de hecho y se documenta explicitamente que el alcance es por lote, no universal.

## Definicion De Hecho

Un convenio CDI queda `complete` solo si cumple todo esto:

1. Pais canonico e identificador estable.
2. Fuente oficial identificada y accesible.
3. Texto o ficha oficial cargada con `source_url`, `capture_date` y hash o equivalente.
4. Fechas clave trazadas: firma, entrada en vigor y efectos, si la fuente las publica.
5. BOE/protocolo/enmienda enlazados cuando existan.
6. Articulos minimos indexados con referencia estable.
7. Tipos de renta prioritarios mapeados a articulo y condicion.
8. API o MCP expone consulta por pais, articulo y tipo de renta.
9. Tests de contrato cubren encontrado, no encontrado y evidencia parcial.
10. Respuesta `fail-closed` cuando falte articulo, tasa, protocolo o evidencia.

Si falla un punto, el convenio no puede marcarse `complete`.

## Alcance Inicial

### Pais piloto

Primer lote recomendado, por valor fiscal y frecuencia de uso:

| Pais | Hipotesis inicial | Motivo | Accion inicial |
| --- | --- | --- | --- |
| Estados Unidos | `partial` | Hay endpoints y seed historico `ES_US_DTA`, pero falta contrato articulo/renta completo | Auditar fuente oficial, protocolo y reglas por tipo de renta |
| Reino Unido | `target` | Pais prioritario, no asumir cierre sin prueba por articulo | Confirmar fuente y estructura |
| Francia | `target` | Pais prioritario UE | Confirmar fuente y estructura |
| Alemania | `target` | Pais prioritario UE | Confirmar fuente y estructura |
| Italia | `target` | Pais prioritario UE | Confirmar fuente y estructura |
| Portugal | `target` | Pais prioritario de proximidad | Confirmar fuente y estructura |
| Paises Bajos | `target` | Pais frecuente en estructuras holding | Confirmar fuente y estructura |
| Luxemburgo | `target` | Pais frecuente en estructuras financieras | Confirmar fuente y estructura |
| Suiza | `target` | Pais prioritario no UE | Confirmar fuente y estructura |
| Irlanda | `target` | Pais frecuente en tecnologia/royalties | Confirmar fuente y estructura |
| Mexico | `target` | Pais prioritario LatAm | Confirmar fuente y estructura |
| Brasil | `target` | Pais prioritario LatAm | Confirmar fuente y estructura |

La hipotesis por pais es deliberadamente conservadora. Que el worker historico haya cargado 86 convenios no convierte automaticamente cada pais en `partial`: hasta auditar fuente, articulo, protocolo y tipo de renta, el pais queda `target` para este PRD. Estados Unidos se mantiene como `partial` solo porque existe evidencia de superficie concreta en tests/endpoints (`ES_US_DTA`), pero no se considera cerrado.

### Tipos de renta minimos

- dividendos
- intereses
- canones
- ganancias_patrimoniales
- establecimiento_permanente
- servicios_profesionales
- otras_rentas

## Modelo De Datos Objetivo

No es obligatorio crear estas tablas con estos nombres exactos, pero el contrato debe cubrir estos conceptos.

| Entidad | Campos minimos |
| --- | --- |
| `cdi_convenio` | `id`, `pais`, `pais_iso2`, `pais_slug`, `codigo`, `titulo`, `estado`, `fecha_firma`, `fecha_vigencia`, `fecha_efectos`, `boe_referencia`, `source_url`, `source_hash`, `capture_date`, `verified`, `completeness` |
| `cdi_articulo` | `convenio_id`, `numero`, `titulo`, `texto`, `source_url`, `source_hash`, `capture_date`, `verified`, `completeness` |
| `cdi_tipo_renta` | `convenio_id`, `tipo_renta`, `articulo_referencia`, `tasa`, `condiciones`, `protocolo_referencia`, `verified`, `completeness` |
| `cdi_modelo_relacion` | `convenio_id`, `modelo_aeat`, `tipo_renta`, `relacion`, `nota_limitacion` |
| `source_revision` | Reutilizar para cambios de fuente, si encaja con el worker actual |

Si se mantiene `irs_dta_convention`, debe documentarse por que el nombre sigue siendo valido para CDI Espana y que campos faltan frente a este contrato.

## Contrato API/MCP

### API minima

- `GET /v1/internacional/convenios`
- `GET /v1/internacional/convenios/{codigo}`
- `GET /v1/internacional/convenios/{codigo}/articulos/{numero}`
- `GET /v1/internacional/convenios/retenciones?pais=&tipo_renta=`
- `POST /v1/internacional/convenios/retencion`
- `GET /v1/internacional/convenios/coverage`

### MCP minimo

- `listar_convenios_dta_internacional`
- `detalle_convenio_dta_internacional`
- `listar_reglas_retencion_internacional`
- `calcular_retencion`
- `cdi_coverage`

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

- el pais no existe en el corpus cargado,
- el convenio existe pero no tiene articulo cargado para el tipo de renta,
- la tasa depende de protocolo/enmienda no cargada,
- la respuesta exige aplicar derecho domestico no modelado,
- la fuente oficial no tiene URL o fecha de captura trazable,
- el dato procede de seed historico sin evidencia oficial suficiente.

No se debe devolver una tasa como definitiva solo porque exista un convenio vigente.

## Revision De Coherencia 2026-05-20

La revision activa confirma esta clasificacion:

| Superficie | Estado coherente | Motivo |
| --- | --- | --- |
| Matriz fiscal-regulatoria | `implemented_partial` | Hay worker, endpoints, MCP y evidencia historica, pero falta cierre por convenio/articulo/renta |
| Backlog de expansion | `implemented_partial` | Ya no debe figurar como `target` puro porque la infraestructura existe |
| Hipotesis por pais | conservadora | Solo Estados Unidos parte como `partial`; el resto del lote queda `target` hasta auditoria por fuente y articulo |
| Manual de usuario | evidencia limitada | Los endpoints son exploratorios/operativos sobre datos cargados, no una calculadora fiscal definitiva |

Regla de coherencia: "convenio cargado", "convenio consultable" y "convenio utilizable para calcular retencion con evidencia suficiente" son estados distintos. La documentacion no debe tratarlos como equivalentes.

## Tareas

1. Auditar el estado real de `irs_dta_convention` y `irs_withholding_rule` en produccion.
2. Confirmar si los 86 convenios cargados tienen fuente oficial, BOE, PDF y fechas suficientes.
3. Decidir si se crea familia `cdi_*` o si se endurece `irs_dta_convention` con contrato CDI Espana.
4. Definir el lote piloto de 12 paises.
5. Implementar o endurecer ingestion por pais, articulo y tipo de renta.
6. Exponer `coverage` por pais y tipo de renta.
7. Endurecer API/MCP con `verified`, `completeness`, `safe_to_answer` y `evidence_notice`.
8. Crear tests de contrato para encontrado, parcial, no encontrado y falta de evidencia.
9. Actualizar matriz fiscal-regulatoria y manual si cambia comportamiento visible.
10. Documentar gaps por pais y siguiente accion.

## Criterios De Aceptacion

1. CDI aparece como familia propia, no como anexo generico de AEAT.
2. La matriz clasifica CDI como `implemented_partial` hasta cerrar el contrato por lote.
3. Existe inventario de paises con estado por pais.
4. Cada respuesta de convenio o retencion declara evidencia y completitud.
5. El calculo de retencion no aplica tasas reducidas sin articulo/protocolo trazable.
6. Los tests fallan si una respuesta factual no incluye evidencia.
7. El worker no inserta convenios sin fuente oficial trazable.
8. Los gaps quedan documentados por pais, articulo o tipo de renta.

## Entregables

- Inventario CDI por pais.
- Contrato de cobertura CDI.
- Worker o seed reproducible con fuentes oficiales.
- API/MCP endurecido.
- Tests de contrato.
- Actualizacion de `docs/fiscal-regulatory-coverage-matrix.md`.
- Actualizacion de manual si cambia la respuesta funcional de los endpoints.

## Resultado Esperado

La respuesta correcta a "CDI esta hecho?" debe ser:

> CDI existe como superficie parcial: hay worker, endpoints y carga historica de convenios. No esta cerrado como producto fiscal completo hasta auditar pais por pais, mapear articulos y tipos de renta, y hacer que API/MCP respondan con evidencia y abstencion segura.

# AEAT priority model closeout

## Objetivo

Cerrar el nucleo fiscal AEAT por modelo prioritario, sin tratar `AEAT` como un bloque unico. Cada modelo queda clasificado como `complete`, `partial`, `target`, `configured_but_unavailable` u `out_of_scope` segun evidencia verificable.

Esta primera pasada usa evidencia productiva ya capturada en el repo para `v1.13.1`:

- `docs/aeat-models-a13-20260520.md`
- `docs/population-report-20260520.md`
- `docs/aeat-docs-map.md`
- `docs/aeat-documentation-coverage-report.md`
- `docs/aeat-instructions-coverage-report.md`
- `scripts/maintenance/mcp_validation_suite.py`
- `apps/api/tests/test_modelos_truth_contract.py`

No ejecuta nuevos workers ni carga datos. Cuando un modelo no tiene evidencia suficiente para cumplir los ocho criterios de hecho, queda como `partial` o `target`.

## Criterio de hecho

Un modelo AEAT solo puede quedar `complete` si cumple los ocho puntos:

1. Fuente oficial identificada.
2. Worker o seed reproducible.
3. Datos en produccion.
4. API o MCP expuesto.
5. Metadatos de evidencia: `verified`, `completeness`, `source_url`, `capture_date` o equivalente.
6. Tests de contrato.
7. Documentacion de cobertura.
8. Respuesta `fail-closed` cuando falte evidencia.

Si falta un punto, el modelo no puede marcarse `complete`.

## Resumen final

### Complete

- `187`
- `193`
- `198`
- `216`
- `290`
- `296`

### Partial

- `100`
- `111`
- `115`
- `123`
- `124`
- `200`
- `202`
- `289`
- `303`

### Target

- `180`
- `184`
- `190`
- `232`
- `233`
- `347`
- `349`
- `390`

### Configured but unavailable

- Ninguno en esta pasada.

### Out of scope

- Ninguno del conjunto prioritario.

## Tabla de cierre

| Modelo | Hipotesis inicial | Estado final | Evidencia principal | Gap principal | Siguiente accion |
| --- | --- | --- | --- | --- | --- |
| 187 | complete probable | `complete` | `docs/aeat-instructions-coverage-report.md`: 28 claves, 5 instrucciones, `completa`, `verified=true`; D-13: 50 casillas desde PDF logico AEAT | Sin gap critico para el alcance actual | Mantener regression de contrato y freshness |
| 193 | complete probable | `complete` | `docs/aeat-instructions-coverage-report.md`: 38 claves, 5 instrucciones, `completa`, `verified=true`; D-13: 71 casillas desde PDF logico AEAT | Sin gap critico para el alcance actual | Mantener regression de contrato y freshness |
| 198 | complete probable | `complete` | `docs/aeat-instructions-coverage-report.md`: 46 claves, 7 instrucciones, `completa`, `verified=true`; `mcp_validation_suite.py` valida `/v1/modelos/aeat/198` como completed contract | Sin gap critico para el alcance actual | Mantener `aeat_modelo_198_completed_contract` |
| 216 | complete probable | `complete` | `docs/aeat-instructions-coverage-report.md`: 5 claves, 6 instrucciones, `completa`, `verified=true`; D-13: 47 casillas XLSX AEAT | Sin gap critico para el alcance actual | Mantener contrato IRNR y no mezclar con FATCA/CRS |
| 290 | complete probable | `complete` | `docs/aeat-instructions-coverage-report.md`: 7 claves, 7 instrucciones, 5 reglas, `completa`, `verified=true`; `mcp_validation_suite.py` valida FATCA y evita contaminacion IRNR | El subdominio FATCA/IRS amplio sigue fuera del cierre del modelo | Mantener Modelo 290 como complete por modelo y abrir PRD separado para familia FATCA/IRS si procede |
| 296 | complete probable | `complete` | `docs/aeat-instructions-coverage-report.md`: 35 claves, 8 instrucciones, `completa`, `verified=true`; D-13: 124 casillas desde PDF logico AEAT | Sin gap critico para el alcance actual | Mantener contrato IRNR anual y pruebas de no contaminacion |
| 100 | partial probable | `partial` | D-13: 2.521 casillas desde XSD/diccionarios AEAT y contrato documental `completa`; `test_modelos_truth_contract.py` mantiene subendpoints/fuentes como `parcial`, `verified=false` | Conflicto de granularidad: formulario/casillas fuerte, pero fuentes/subendpoints y campana-operativa no cumplen cierre completo | Reconciliar contrato runtime por subendpoint antes de graduar a `complete` |
| 111 | partial probable | `partial` | D-13: 63 casillas desde XLS AEAT, `verified=false`, `parcial`; `modelos_por_supuesto` lo excluye de confirmacion para sociedad de valores | Falta instrucciones/claves/reglas y aplicabilidad contractual completa | Cargar instrucciones/claves oficiales o dejar evidencia limitada explicita |
| 115 | partial probable | `partial` | D-13: 37 casillas desde XLS AEAT, `verified=false`, `parcial`; `modelos_por_supuesto` lo excluye de confirmacion | Falta instrucciones/claves/reglas y aplicabilidad contractual completa | Cargar instrucciones/claves oficiales y test de contrato |
| 123 | partial probable | `partial` | D-13: 44 casillas desde XLS AEAT, `verified=false`, `parcial`; catalogo AEAT prueba capa sin evidencia de perfil | Falta profundidad documental y confirmacion de aplicabilidad por supuesto | Completar instrucciones/claves o mantener como candidato con review_required |
| 124 | partial probable | `partial` | D-13: 39 casillas desde XLSX AEAT, `verified=false`, `parcial`; aparece como candidato, no confirmado, en contrato por supuesto | Falta profundidad documental y confirmacion de aplicabilidad por supuesto | Completar instrucciones/claves o mantener como candidato con review_required |
| 200 | partial probable | `partial` | D-13: 6.807 casillas desde XLS/anexos AEAT; `docs/aeat-instructions-coverage-report.md`: 5 instrucciones, `parcial`, `verified=false` | Sin conjunto determinista de claves/reglas completo; contrato sigue parcial | Determinar gap exacto de IS: claves, reglas y aplicabilidad operativa |
| 202 | partial probable | `partial` | `mcp_validation_suite.py` valida obligacion Modelo 202 por perfiles y calendario; no hay cierre documental especifico equivalente a D-13/I-11 | Evidencia de obligacion/aplicabilidad, pero no cierre completo de formulario/instrucciones/casillas por modelo | Crear mini-auditoria Modelo 202: fuente, casillas, instrucciones, plazo y perfil |
| 289 | partial probable | `partial` | `mcp_validation_suite.py` exige normativa >=4, instrucciones >=5, reglas >=6, keywords >=8, casillas >=20 y obligaciones verificadas; D-13 conserva contrato parcial | CRS/DAC2 tiene buena base, pero el procedimiento completo y contrato de modelo siguen sin graduarse a `complete` | Separar cierre del formulario 289 de PRD CRS/DAC2 operativo |
| 303 | partial probable | `partial` | D-13: 432 casillas desde XLSX AEAT 300-399; `docs/aeat-instructions-coverage-report.md`: 5 instrucciones, `parcial`, `verified=false`; tests fuerzan parcial en campana-operativa | Falta precision operativa/reglas/claves suficientes; contrato runtime parcial | Auditar quirurgicamente IVA 303 para decidir cierre o gaps finales |
| 180 | target/auditar | `target` | Hay referencias legacy/seed y calendario en el repo, pero no cierre oficial en D-13/I-11 ni contrato especifico por modelo prioritario | Base insuficiente para tratarlo como producto cerrado | Auditar desde fuente AEAT y decidir si entra a `partial` |
| 184 | target/auditar | `target` | Hay referencias legacy/seed, pero no cierre oficial en D-13/I-11 ni contrato especifico por modelo prioritario | Base insuficiente para tratarlo como producto cerrado | Auditar desde fuente AEAT y decidir si entra a `partial` |
| 190 | target/auditar | `target` | Existe clasificacion en `aeat_models.py` y referencias de calendario/seed; `modelos_por_supuesto` lo excluye de confirmacion | No hay cierre documental de casillas/instrucciones/reglas en los informes activos | Auditar Modelo 190 como candidato de alto impacto |
| 232 | target/auditar | `target` | Sin evidencia suficiente localizada en informes activos de cierre AEAT prioritario | Falta fuente/carga/contrato documentados para el alcance de este PRD | Localizar fuente oficial y decidir si merece PRD propio |
| 233 | target/auditar | `target` | `docs/aeat-documentation-coverage-report.md`: `STATUS-E`, pendiente de localizar contrato/plantilla oficial determinista | Fuente determinista no localizada; no se debe inventar contrato desde ejemplos | Mantener target hasta localizar plantilla oficial determinista |
| 347 | target/auditar | `target` | Hay referencias seed/calendario y clasificacion en `aeat_models.py`, pero no cierre oficial D-13/I-11 | Falta evidencia productiva de casillas/instrucciones/reglas y contrato especifico | Auditar desde fuente AEAT por volumen e impacto |
| 349 | target/auditar | `target` | Hay referencias seed/calendario y clasificacion en `aeat_models.py`, pero no cierre oficial D-13/I-11 | Falta evidencia productiva de casillas/instrucciones/reglas y contrato especifico | Auditar desde fuente AEAT, especialmente aplicabilidad intracomunitaria |
| 390 | target/auditar | `target` | Hay referencias de articulo/instrucciones legacy, pero no cierre oficial D-13/I-11 | Falta evidencia productiva y contrato de modelo completo | Auditar Modelo 390 como cierre IVA anual posterior a 303 |

## Entradas por modelo

### Modelo 187

- Estado final: `complete`.
- Hipotesis inicial: complete probable.
- Fuente oficial: PDF logico AEAT, `DR_Modelo_187_2022.pdf`.
- Produccion: D-13 reporta 50 casillas; I-11 reporta 28 claves y 5 instrucciones.
- API/MCP: contrato `completa`, `verified=true` segun `docs/aeat-instructions-coverage-report.md`.
- Tests: validado por suite completa I-11; conservar como regression.
- Documentacion: `docs/aeat-docs-map.md`, `docs/aeat-documentation-coverage-report.md`, `docs/aeat-instructions-coverage-report.md`.
- Gaps: sin gap critico para el alcance de modelo.
- Siguiente accion: mantener freshness y tests.

### Modelo 193

- Estado final: `complete`.
- Hipotesis inicial: complete probable.
- Fuente oficial: PDF logico AEAT 2025, `DR_Modelo_193_2025.pdf`.
- Produccion: D-13 reporta 71 casillas; I-11 reporta 38 claves y 5 instrucciones.
- API/MCP: contrato `completa`, `verified=true`.
- Tests: validado por suite completa I-11; conservar como regression.
- Documentacion: informes D-13/I-11.
- Gaps: sin gap critico para el alcance de modelo.
- Siguiente accion: mantener contrato capital mobiliario.

### Modelo 198

- Estado final: `complete`.
- Hipotesis inicial: complete probable.
- Fuente oficial: PDF logico AEAT 2024, `DR_Modelo_198_2024.pdf`.
- Produccion: D-13 reporta 72 casillas; I-11 reporta 46 claves y 7 instrucciones.
- API/MCP: `mcp_validation_suite.py` contiene `aeat_modelo_198_completed_contract`.
- Tests: suite I-11 y contrato MCP especifico.
- Documentacion: informes D-13/I-11.
- Gaps: sin gap critico para el alcance de modelo.
- Siguiente accion: mantener test especifico.

### Modelo 216

- Estado final: `complete`.
- Hipotesis inicial: complete probable.
- Fuente oficial: XLSX AEAT 2024, `216e2024.xlsx`.
- Produccion: D-13 reporta 47 casillas; I-11 reporta 5 claves y 6 instrucciones.
- API/MCP: contrato `completa`, `verified=true`.
- Tests: suite I-11 y tests de no contaminacion FATCA/IRNR.
- Documentacion: informes D-13/I-11.
- Gaps: sin gap critico para el alcance de modelo.
- Siguiente accion: mantener separado de FATCA/CRS.

### Modelo 290

- Estado final: `complete`.
- Hipotesis inicial: complete probable.
- Fuente oficial: ZIP XSD/WSDL AEAT FATCA y fuentes BOE/AEAT de instrucciones.
- Produccion: D-13 reporta 152 casillas; I-11 reporta 7 claves, 7 instrucciones y 5 reglas.
- API/MCP: `mcp_validation_suite.py` valida `/v1/modelos/aeat/290` y consulta FATCA hacia 290 sin IRNR.
- Tests: `modelo_290_fatca_rules_contract` y `consulta_fatca_routes_to_modelo_290`.
- Documentacion: informes D-13/I-11.
- Gaps: FATCA/IRS como familia amplia sigue fuera de este cierre.
- Siguiente accion: abrir PRD FATCA/IRS si se quiere ampliar mas alla del modelo.

### Modelo 296

- Estado final: `complete`.
- Hipotesis inicial: complete probable.
- Fuente oficial: PDF logico AEAT 2024, `DR_296_2024.pdf`.
- Produccion: D-13 reporta 124 casillas; I-11 reporta 35 claves y 8 instrucciones.
- API/MCP: contrato `completa`, `verified=true`.
- Tests: suite I-11 y tests de routing IRNR/FATCA.
- Documentacion: informes D-13/I-11.
- Gaps: sin gap critico para el alcance de modelo.
- Siguiente accion: mantener regression IRNR anual.

### Modelo 100

- Estado final: `partial`.
- Hipotesis inicial: partial probable.
- Fuente oficial: XSD y diccionarios AEAT 2025.
- Produccion: D-13 reporta 2.521 casillas y contrato documental `completa`.
- API/MCP: los tests de runtime mantienen `/v1/modelos/100/fuentes-oficiales`, `/casillas`, `/claves` e `/instrucciones` como `parcial`, `verified=false`.
- Tests: `test_modelo_subendpoints_keep_partial_truth_contract_for_model_100`.
- Documentacion: D-13 y tests actuales discrepan en granularidad de cierre.
- Gaps: contrato runtime por subendpoint no esta reconciliado con cierre documental.
- Siguiente accion: reconciliar contrato por subendpoint antes de graduar.

### Modelo 111

- Estado final: `partial`.
- Hipotesis inicial: partial probable.
- Fuente oficial: XLS AEAT.
- Produccion: D-13 reporta 63 casillas.
- API/MCP: contrato `parcial`, `verified=false`.
- Tests: `modelos_por_supuesto` lo excluye de confirmacion para sociedad de valores.
- Documentacion: D-13.
- Gaps: faltan instrucciones/claves/reglas y aplicabilidad cerrada.
- Siguiente accion: cargar instrucciones/claves oficiales o documentar limite permanente.

### Modelo 115

- Estado final: `partial`.
- Hipotesis inicial: partial probable.
- Fuente oficial: XLS AEAT.
- Produccion: D-13 reporta 37 casillas.
- API/MCP: contrato `parcial`, `verified=false`.
- Tests: `modelos_por_supuesto` lo excluye de confirmacion.
- Documentacion: D-13.
- Gaps: faltan instrucciones/claves/reglas y aplicabilidad cerrada.
- Siguiente accion: cargar instrucciones/claves oficiales.

### Modelo 123

- Estado final: `partial`.
- Hipotesis inicial: partial probable.
- Fuente oficial: XLS AEAT.
- Produccion: D-13 reporta 44 casillas.
- API/MCP: catalogo AEAT probado sin evidence de perfil; `/por-supuesto` lo mantiene como candidato prudente.
- Tests: `aeat_catalogo_no_profile_evidence_contract`, `test_aeat_123_124_capital_mobiliario_rules_are_seeded_in_revision_0092`.
- Documentacion: D-13 y `docs/aeat-capital-mobiliario-123-124-193-routing.md`.
- Gaps: falta profundidad documental, claves/instrucciones deterministicas y aplicabilidad por supuesto.
- Siguiente accion: completar claves/instrucciones oficiales si existe fuente determinista; no promover por casillas.

### Modelo 124

- Estado final: `partial`.
- Hipotesis inicial: partial probable.
- Fuente oficial: XLSX AEAT.
- Produccion: D-13 reporta 39 casillas.
- API/MCP: no aparece como candidato por capital mobiliario residente generico; solo se ofrece como candidato si el supuesto identifica transmision, amortizacion, reembolso, canje o conversion de activos financieros.
- Tests: `test_modelos_por_supuesto_sociedad_valores_fail_closed_without_explicit_obligation`, `test_modelos_por_supuesto_includes_124_only_for_specific_financial_asset_operation`, `test_aeat_123_124_capital_mobiliario_rules_are_seeded_in_revision_0092`.
- Documentacion: D-13.
- Documentacion adicional: `docs/aeat-capital-mobiliario-123-124-193-routing.md`.
- Cambios Sprint S: metadato fiscal corregido a `IRPF/IS/IRNR`; reglas `CONDICIONAL`/`EXCLUIR` persistidas desde ficha AEAT `GH05` si hay hash/captura.
- Gaps: falta profundidad documental, claves/instrucciones especificas y aplicabilidad por supuesto.
- Siguiente accion: completar instrucciones/claves especificas de activos financieros si existe fuente determinista o mantener excluido/candidato condicionado.

### Modelo 200

- Estado final: `partial`.
- Hipotesis inicial: partial probable.
- Fuente oficial: XLS y anexos AEAT.
- Produccion: D-13 reporta 6.807 casillas; I-11 reporta 5 instrucciones.
- API/MCP: `parcial`, `verified=false`.
- Tests: suite I-11 mantiene caveat.
- Documentacion: D-13/I-11.
- Gaps: no hay conjunto determinista completo de claves/reglas.
- Siguiente accion: definir cierre de IS por claves, reglas y aplicabilidad operativa.

### Modelo 202

- Estado final: `partial`.
- Hipotesis inicial: partial probable.
- Fuente oficial: AEAT/BOE segun obligaciones de perfil existentes.
- Produccion: `mcp_validation_suite.py` verifica Modelo 202 en obligaciones por perfiles y calendario.
- API/MCP: existe como obligacion fiscal verificada, pero no como cierre completo de formulario.
- Tests: `modelo_202_all_profiles_loaded` y validaciones de calendario.
- Documentacion: roadmap Sprint G.
- Gaps: no hay closeout documental de casillas/instrucciones/reglas equivalente a D-13/I-11.
- Siguiente accion: mini-auditoria del Modelo 202 como formulario.

### Modelo 289

- Estado final: `partial`.
- Hipotesis inicial: partial probable.
- Fuente oficial: ZIP XSD/WSDL AEAT y manual CRS/DAC2.
- Produccion: D-13 reporta 134 casillas; mcp suite exige normativa, instrucciones, reglas, keywords y obligaciones verificadas.
- API/MCP: contrato CRS fuerte, pero no graduado a complete por procedimiento global.
- Tests: `modelo_289_*` y `aeat_catalogo_modelo_289_crs_counts`.
- Documentacion: D-13, Sprint J y source backlog.
- Gaps: procedimiento CRS/DAC2 completo y familia CRS siguen abiertos.
- Siguiente accion: separar cierre de formulario 289 de PRD CRS/DAC2.

### Modelo 303

- Estado final: `partial`.
- Hipotesis inicial: partial probable.
- Fuente oficial: XLSX AEAT 300-399.
- Produccion: D-13 reporta 432 casillas; I-11 reporta 5 instrucciones.
- API/MCP: contrato `parcial`, `verified=false`; campana-operativa inferida en tests.
- Tests: `test_modelo_detail_marks_partial_when_campaign_lacks_official_instructions` y `test_modelo_campana_operativa_marks_partial_when_runtime_is_inferred`.
- Documentacion: D-13/I-11.
- Gaps: falta precision operativa, reglas y contrato suficiente.
- Siguiente accion: auditoria quirurgica IVA 303.

### Modelo 180

- Estado final: `target`.
- Hipotesis inicial: target/auditar.
- Fuente oficial: no cerrada en informes activos.
- Produccion: referencias legacy/seed, sin cierre AEAT prioritario.
- API/MCP: sin contrato especifico de cierre.
- Tests: sin test de contrato de modelo.
- Documentacion: no aparece en D-13/I-11 como modelo cerrado.
- Gaps: fuente/casillas/instrucciones/reglas no verificadas.
- Siguiente accion: auditar desde fuente AEAT.

### Modelo 184

- Estado final: `target`.
- Hipotesis inicial: target/auditar.
- Fuente oficial: no cerrada en informes activos.
- Produccion: referencias legacy/seed, sin cierre AEAT prioritario.
- API/MCP: sin contrato especifico de cierre.
- Tests: sin test de contrato de modelo.
- Documentacion: no aparece en D-13/I-11 como modelo cerrado.
- Gaps: fuente/casillas/instrucciones/reglas no verificadas.
- Siguiente accion: auditar desde fuente AEAT.

### Modelo 190

- Estado final: `target`.
- Hipotesis inicial: target/auditar.
- Fuente oficial: no cerrada en informes activos.
- Produccion: clasificacion e inventario probable, pero sin closeout.
- API/MCP: `modelos_por_supuesto` lo excluye de confirmacion.
- Tests: exclusion en `test_modelos_por_supuesto_sociedad_valores_fail_closed_without_explicit_obligation`.
- Documentacion: no aparece en D-13/I-11 como modelo cerrado.
- Gaps: sin casillas/instrucciones/reglas verificadas en closeout.
- Siguiente accion: auditar por impacto laboral/retenciones.

### Modelo 232

- Estado final: `target`.
- Hipotesis inicial: target/auditar.
- Fuente oficial: no localizada en informes activos de cierre.
- Produccion: sin evidencia suficiente en esta pasada.
- API/MCP: sin contrato especifico.
- Tests: sin test de contrato.
- Documentacion: no aparece en D-13/I-11.
- Gaps: fuente y carga no documentadas.
- Siguiente accion: localizar fuente oficial y decidir inversion.

### Modelo 233

- Estado final: `target`.
- Hipotesis inicial: target/auditar.
- Fuente oficial: pendiente de localizar contrato/plantilla determinista.
- Produccion: D-13 lo clasifica como `STATUS-E`.
- API/MCP: debe responder con evidencia limitada si se consulta.
- Tests: Q-02 valida parciales como 233 con `evidence_limited`.
- Documentacion: `docs/aeat-documentation-coverage-report.md`.
- Gaps: no hay plantilla/contrato oficial determinista.
- Siguiente accion: mantener target hasta localizar fuente determinista.

### Modelo 347

- Estado final: `target`.
- Hipotesis inicial: target/auditar.
- Fuente oficial: no cerrada en informes activos.
- Produccion: referencias seed/calendario, sin cierre AEAT prioritario.
- API/MCP: sin contrato especifico de cierre.
- Tests: sin test de contrato de modelo.
- Documentacion: no aparece en D-13/I-11 como modelo cerrado.
- Gaps: falta evidencia productiva de casillas/instrucciones/reglas.
- Siguiente accion: auditar por volumen e impacto operativo.

### Modelo 349

- Estado final: `target`.
- Hipotesis inicial: target/auditar.
- Fuente oficial: no cerrada en informes activos.
- Produccion: referencias seed/calendario, sin cierre AEAT prioritario.
- API/MCP: sin contrato especifico de cierre.
- Tests: sin test de contrato de modelo.
- Documentacion: no aparece en D-13/I-11 como modelo cerrado.
- Gaps: falta evidencia productiva de casillas/instrucciones/reglas.
- Siguiente accion: auditar aplicabilidad intracomunitaria.

### Modelo 390

- Estado final: `target`.
- Hipotesis inicial: target/auditar.
- Fuente oficial: no cerrada en informes activos.
- Produccion: referencias legacy de articulo/instrucciones, sin cierre AEAT prioritario.
- API/MCP: sin contrato especifico de cierre.
- Tests: sin test de contrato de modelo.
- Documentacion: no aparece en D-13/I-11 como modelo cerrado.
- Gaps: falta evidencia productiva y contrato completo.
- Siguiente accion: auditar despues de resolver IVA 303.

## Gaps criticos

| Modelo | Gap | Accion |
| --- | --- | --- |
| 100 | Contrato documental fuerte pero subendpoints runtime parciales | Reconciliar `verified/completeness` por subendpoint |
| 200 | Casillas masivas e instrucciones parciales sin claves/reglas completas | Definir cierre de IS |
| 202 | Obligacion/perfil validada, formulario no cerrado | Mini-auditoria Modelo 202 |
| 289 | CRS fuerte pero procedimiento/familia no cerrados | Separar cierre modelo de PRD CRS/DAC2 |
| 303 | IVA prioritario con contrato parcial | Auditoria quirurgica de reglas e instrucciones |
| 180/184/190/232/347/349/390 | Sin closeout oficial por modelo | Auditar fuente AEAT y pasar a `partial` solo con evidencia |
| 233 | `STATUS-E` sin plantilla determinista | Localizar fuente oficial no autenticada/determinista |

## Respuesta a "AEAT esta hecho"

AEAT no esta cerrado como bloque unico.

Estado de los modelos prioritarios de este PRD:

- 6 modelos `complete`: `187`, `193`, `198`, `216`, `290`, `296`.
- 9 modelos `partial`: `100`, `111`, `115`, `123`, `124`, `200`, `202`, `289`, `303`.
- 8 modelos `target`: `180`, `184`, `190`, `232`, `233`, `347`, `349`, `390`.

El cierre fiscal AEAT debe leerse modelo por modelo. Los subdominios `CDI`, fiscalidad territorial, DGT/TEAC y jurisprudencia tributaria quedan fuera de este PRD.

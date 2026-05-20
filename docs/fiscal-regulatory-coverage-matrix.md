# Matriz de cobertura fiscal-regulatoria

## Objetivo

Esta matriz es una referencia viva para distinguir que dominios fiscales y regulatorios estan realmente listos, cuales estan parcialmente implementados y cuales siguen pendientes.

No sustituye a `docs/master-execution-roadmap.md` como fuente de estado activo. Su funcion es evitar afirmaciones ambiguas como "AEAT esta hecho" cuando el dominio contiene subpartes completas, parciales y pendientes.

## Fuentes de lectura

- `docs/master-execution-roadmap.md`
- `docs/source-expansion-backlog-2026-05-17.md`
- `docs/population-report-20260520.md`
- `docs/manual-usuario/05-limites-alcance-y-estado-actual.md`
- Informes de cobertura especificos en `docs/*coverage*.md`

## Definicion de hecho

Una familia solo puede marcarse como `complete` si cumple los ocho puntos:

1. Fuente oficial identificada.
2. Worker o seed reproducible.
3. Datos en produccion.
4. API o MCP expuesto.
5. Metadatos de evidencia: `verified`, `completeness`, `source_url`, `capture_date` o equivalente.
6. Tests de contrato.
7. Documentacion de cobertura.
8. Respuesta `fail-closed` cuando falte evidencia.

Si falta uno de estos puntos, la familia no debe marcarse como `complete`.

## Estados permitidos

- `complete`: listo como producto auditable.
- `implemented_loaded`: cargado y usable, pero no necesariamente completo.
- `implemented_partial`: existe implementacion y datos, pero falta cobertura, contrato o profundidad.
- `ready_for_ingestion`: codigo preparado, falta carga productiva.
- `target`: identificado, pendiente de implementar.
- `configured_but_unavailable`: fuente conocida pero no accesible o bloqueada.
- `out_of_scope`: deliberadamente fuera del alcance actual.

## Matriz inicial

| Dominio | Subdominio | Estado | Fuente oficial | Produccion | API | MCP | Evidencia | Tests | Gaps | Siguiente accion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AEAT | Modelos fiscales | `implemented_partial` | Sede AEAT, recursos oficiales de modelos | 219 modelos y 31.685 casillas en baseline A-14; closeout prioritario: 6 `complete`, 9 `partial`, 8 `target` | si | si | Mixta: varios modelos con `verified` y fuentes oficiales; estado por modelo en `docs/aeat-priority-model-closeout.md` | si | AEAT no esta cerrado como bloque unico; quedan modelos parciales y target | Ejecutar PRDs derivados para 100/200/202/289/303 y bloque target |
| AEAT | Calendario fiscal | `implemented_partial` | Calendario del contribuyente AEAT | Calendario 2026 cargado por worker AEAT actual | si | parcial | Parcial: fechas oficiales, pero no todo supuesto tiene aplicabilidad cerrada | parcial | Falta matriz completa perfil -> modelo -> periodo -> plazo | Conectar calendario con perfiles y obligaciones fiscales prioritarias |
| AEAT | Instrucciones, claves y reglas | `implemented_partial` | Sede AEAT, BOE, XSD/XLS/PDF oficiales | 179 claves y 70 instrucciones en baseline A-14; 187/193/198/216/290/296 completos en informe; 200/303 parciales | si | si | Mixta por modelo: `verified`, instrucciones, claves y reglas donde existen | si | Cobertura desigual entre modelos; falta contrato uniforme para todos los prioritarios | Crear checklist por modelo: instrucciones, claves, reglas, casillas y fuente |
| AEAT | CDI y fiscalidad internacional | `target` | AEAT y Hacienda CDI | Sin tabla propia ni carga declarada como produccion | no | no | no | no | Convenios de doble imposicion fuera del corpus fiscal operativo | Disenar ingesta CDI por pais, articulo y tipo de renta |
| AEAT | CRS/FATCA | `implemented_partial` | AEAT GI42/GI38, XSD/WSDL oficiales, IRS donde aplique | Modelos 289/290 con reglas e instrucciones parciales/completas segun modelo | si | si | Parcial: 290 fuerte; 289 con evidencia limitada en reportes previos | si | Falta expansion procedimental y fuente IRS explicita para familia FATCA | Separar CRS/FATCA como familia operativa con fuentes AEAT/IRS |
| DGT | Consultas vinculantes | `implemented_loaded` | DGT/PETETE | 18.631 consultas cargadas en snapshot del backlog | si | si | Si: numero, fecha, organo y URL oficial en respuestas verificadas | si | La completitud depende de limites de discovery; falta curacion por linea de criterio | Crear lineas de criterio por impuesto, articulo, modelo y tema |
| TEAC | DYCTEA/resoluciones | `implemented_partial` | Hacienda/TEAC DYCTEA | 558 resoluciones; 286 completas y 272 parciales segun roadmap | si | parcial | Parcial: URLs oficiales y completitud por fila | si | Falta curacion por linea de criterio y cobertura historica mas amplia | Crear lineas de criterio TEAC y ampliar ingesta historica si la fuente lo permite |
| BOE | Legislacion fiscal consolidada | `implemented_partial` | BOE consolidado y datos abiertos BOE | Core fiscal cargado: LIVA, LGT, LIRPF, LIS, TRLIRNR y otras normas relacionadas segun roadmap | si | si | Si en articulos verificados; parcial para universo fiscal completo | si | No equivale a todo derecho fiscal estatal, autonomico y foral | Definir inventario fiscal estatal minimo y detectar leyes faltantes |
| Fiscalidad territorial | Foral, Canarias, Ceuta/Melilla | `target` | Haciendas forales, normativa canaria y fuentes oficiales territoriales | Sin cobertura operativa declarada | no | no | no | no | Fiscalidad espanola incompleta sin regimenes territoriales | Crear PRD de fiscalidad territorial con prioridad Pais Vasco, Navarra y Canarias |
| Jurisprudencia tributaria | CENDOJ/CGPJ | `configured_but_unavailable` | CENDOJ/CGPJ | Sin corpus tributario minimo operativo; CENDOJ tratado como bloqueado/limitado en docs historicos | no | no | no | no | Acceso CENDOJ/SSO pendiente; BOE no es fuente de jurisprudencia | Definir fuente autorizada y alcance minimo de jurisprudencia tributaria |
| Jurisprudencia tributaria | TS, AN y TC tributario seleccionado | `target` | CENDOJ/CGPJ, Tribunal Constitucional y fuentes oficiales judiciales | Sin seleccion tributaria minima declarada como producto | no | no | no | no | No existe corpus curado por impuesto/articulo/modelo | Crear PRD de jurisprudencia tributaria minima sin pretender cobertura masiva |
| CNMV | Documentos y aplicabilidad por perfil | `implemented_partial` | CNMV | 141 documentos CNMV; `sociedad_valores=141`, `sgiic=104`; modelos ESI y obligaciones CNMV cargadas | si | si | Parcial: familias y `sujeto_obligado` donde aplica; registros oficiales fuera | si | Guias, consultas, Q&A y registros oficiales no estan completos | Completar familias CNMV separadas y mantener `/v1/cnmv/coverage` como contrato |
| SEPBLAC | Normativa, obligaciones y guias | `implemented_partial` | SEPBLAC, BOE | 7 normativas, 7 obligaciones, 7 guias; RD 304/2014 cargado | si | parcial | Parcial: documentos oficiales y articulado BOE con fuente | si | Tipologias/listas y obligaciones por sujeto necesitan mas profundidad | Expandir tipologias, sujetos obligados y checks PBC/FT por perfil |
| Banco de Espana | Circulares/regulacion financiera | `implemented_partial` | Banco de Espana | Corpus pequeno cargado segun backlog | si | parcial | Parcial | parcial | Falta expansion de circulares e indice de regulacion financiera | Crear ingesta por familias BdE y cobertura por perfil regulado |
| EUR-Lex | Normativa UE fiscal/regulatoria | `implemented_partial` | EUR-Lex/Publications Office | CELEX curados y articulado para normas de mercado como EMIR, MiFID II, MiFIR, MiCA, DLT | si | si | Mixta: articulado verificado en `eurlex_market`; metadata-only en otros casos | si | No todos los actos UE tienen articulado profundo cargado | Separar `metadata_only` de articulado completo y priorizar actos fiscales/regulatorios |
| ESMA | Markets, reporting y registros | `implemented_partial` | ESMA | MiFIR reporting documents, DLT infrastructures, CASP register y documentos seleccionados | si | si | Parcial: fuentes oficiales y hashes donde cargado | si | FIRDS/FULINS completos no se cargan por decision; Q&A/ISRB aun parcial | Completar Q&A/ISRB seleccionados sin replicar datasets masivos salvo decision explicita |
| MiFID/MiFIR | Obligaciones y reporting | `implemented_partial` | EUR-Lex, ESMA, CNMV | RTS 1/2, MiFID II/MiFIR y documentos ESMA seleccionados cargados | si | si | Parcial: obligaciones verificadas y condicionalidad SI donde aplica | si | Falta convertir todo el regimen en workflows operativos por perfil | Definir checklist operativo MiFID/MiFIR por perfil supervisado |
| DORA | Normativa y obligaciones | `implemented_partial` | EUR-Lex, RTS/ITS UE, EBA/ESMA donde aplique | DORA y RTS/ITS cargados; obligaciones por perfiles segun roadmap | si | si | Parcial: normas y obligaciones verificadas; operativa TIC incompleta | si | Faltan incidentes TIC, terceros, registros de riesgo y tests como workflow | Crear PRD DORA operativo con evidencias y plazos de notificacion |
| MiCA | CASP | `implemented_loaded` | EUR-Lex, ESMA Interim MiCA Register | CASP register con 192 filas verificadas y obligaciones CASP cargadas | si | si | Si para CASP cargado: fuente ESMA, hash/capture_date y obligaciones | si | No cubre todos los subdominios MiCA ni activos cripto | Mantener CASP como subdominio separado y no extrapolar a crypto-assets |
| MiCA | Emisor de token | `implemented_partial` | EUR-Lex MiCA; BdE/CNMV supervisorio pendiente donde aplique | Perfil `emisor_token` con 8 obligaciones MiCA base; ART significativo y EMT parciales | si | si | Parcial: obligaciones verificadas, corpus supervisor ART/EMT vacio | si | Falta corpus supervisor para ART/EMT y documentos operativos | Cargar fuentes supervisoras o mantener gap explicito en respuestas |
| PBC/FT | Ley 10/2010, RD 304/2014, SEPBLAC | `implemented_partial` | BOE, SEPBLAC | LEY10_2010, RD_304_2014 y documentos SEPBLAC cargados | si | parcial | Parcial: articulado BOE y documentos SEPBLAC con fuente | si | Falta granularidad completa por sujeto obligado y tipologias | Crear matriz PBC/FT por sujeto, obligacion, control y evidencia |
| Screening/sanciones | OFAC SDN | `implemented_loaded` | OFAC/Treasury SDN XML oficial | 18.947 entradas OFAC en evidencia VPS TS-011; cron semanal operativo | si | parcial | Si para OFAC: fuente oficial y parser dedicado | si | No extrapolar OFAC a UE/UN/SEPBLAC | Mantener OFAC separado y documentar freshness/cadencia |
| Screening/sanciones | UE sanctions | `configured_but_unavailable` | Comision Europea FSF XML | Worker y cron existen, pero la fuente productiva devuelve HTTP 403 y filas UE siguen 0 | si | parcial | No para datos UE; si para abstencion `safe_to_answer=false` | si | Acceso a fuente UE bloqueado por upstream/session/token | Resolver acceso a FSF o mantener gap explicito en availability |
| Screening/sanciones | UN y SEPBLAC sanctions | `target` | UN, SEPBLAC y fuentes oficiales aplicables | Sin carga productiva declarada | no | no | no | no | Falta parser/carga y contrato de disponibilidad por fuente | Definir alcance UN/SEPBLAC y no mezclarlo con OFAC |

## Lectura recomendada

- No usar una fila parcial para afirmar cobertura completa del dominio.
- Si un usuario pregunta si un dominio "esta hecho", responder por subdominio y estado.
- Un `no` resultado en una familia parcial puede significar "no cargado", no "no existe".
- Los proximos PRD derivados deberian salir de la columna `Siguiente accion`.

## Proximos PRD derivados

1. Cierre AEAT prioritarios por modelo.
2. CDI y fiscalidad internacional.
3. Lineas de criterio DGT/TEAC.
4. Fiscalidad territorial/foral.
5. Jurisprudencia tributaria minima.
6. DORA operativo.
7. PBC/FT por sujeto obligado.

# AEAT 29 Models Resource Audit

Estado: M-03 completado. La tabla recoge el mapa inicial M-00 y la resolucion posterior de fuentes XSD oficiales para los modelos que eran automatizables.

Regla aplicada: solo se clasifica como `STATUS-A` cuando existe fuente oficial estructurada de AEAT con campos/casillas parseables sin inferencia. Si la fuente es formulario dinamico, HTML narrativo, PDF esquematico, FAQ, normativa o ejemplo parcial, queda como `STATUS-D` o `STATUS-E`.

| codigo | nombre | source_url | format | status | reason |
|---|---|---|---|---|---|
| 102 | Modelo 102. IRPF. Segundo plazo del fraccionamiento de la declaracion anual. | https://sede.agenciatributaria.gob.es/Sede/impuestos-tasas/impuesto-sobre-renta-personas-fisicas/modelo-100-mode-declaracion-documentos-devolucion_/descarga-modelo-102.html | HTML form/download | STATUS-B | Documento de ingreso del segundo plazo IRPF; no aparece diseño de registro propio ni fuente estructurada de casillas en la campaña activa. |
| 121 | Modelo 121. IRPF. Deducciones por familia numerosa o discapacidad a cargo. | https://www1.agenciatributaria.gob.es/wlpl/DFND-M121/F121Servlet | AEAT dynamic endpoint | STATUS-D | Formulario dinamico `www1` sin diseño de registro descargable; requiere navegador/flujo o contrato endpoint antes de extraer campos. |
| 136 | Modelo 136. IRPF/IRNR. Gravamen especial sobre premios de loterias. | https://www1.agenciatributaria.gob.es/wlpl/PAMW-M136/index.zul | AEAT dynamic endpoint | STATUS-D | Aplicacion `.zul` dinamica; no hay recurso estructurado en `modelo_recurso` ni diseño de registro especifico. |
| 140 | Modelo 140. IRPF. Deduccion por maternidad. | https://www1.agenciatributaria.gob.es/wlpl/DAMA-PRES/F140Sol | AEAT dynamic endpoint | STATUS-D | Formulario dinamico de solicitud; requiere navegador/contrato endpoint para no inventar campos. |
| 143 | Modelo 143. IRPF. Abono anticipado deducciones familia/discapacidad. | https://sede.agenciatributaria.gob.es/Sede/beneficios-fiscales-autorizaciones/irpf/modelo-143-irpf______do-deducciones-familia-discapacidad_/preguntas-frecuentes.html | HTML FAQ/form help | STATUS-D | Fuente activa enlaza FAQ/ayuda, no tabla de casillas ni diseño estructurado. |
| 146 | Modelo 146. IRPF. Pensionistas con dos o mas pagadores. | https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/impuesto-sobre-renta-personas-fisicas/modelo-146-irpf______d-determinacion-importe-retenciones_/descarga-modelo.html | HTML form/download | STATUS-B | Modelo de solicitud/comunicacion descargable sin diseño de registro estructurado en AEAT. |
| 147 | Modelo 147. IRPF. Comunicacion desplazamiento a territorio espanol. | https://sede.agenciatributaria.gob.es/Sede/impuestos-tasas/impuesto-sobre-renta-personas-fisicas/modelo-147-irpf______panol-efectuado-trabajadores-ajena_/descarga-modelo.html | HTML form/download | STATUS-B | Modelo de comunicacion descargable; no consta fuente oficial estructurada de casillas. |
| 150 | Modelo 150. IRPF. Regimen especial trabajadores desplazados. | https://sede.agenciatributaria.gob.es/Sede/impuestos-tasas/impuesto-sobre-renta-personas-fisicas/modelo-150-irpf______los-trabajadores-desplazados-espanol_/descarga-modelo.html | HTML form/download + country-code PDF | STATUS-D | Hay formulario/ayuda, pero el PDF detectado es catalogo de paises, no casillas del modelo; requiere inspeccion de formulario. |
| 172 | Modelo 172. Declaracion informativa sobre saldos en monedas virtuales. | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI53/Esquemas172.zip | ZIP with WSDL/XSD | STATUS-A | ZIP oficial contiene `DDIIModelo172.wsdl`, `Declaracion172.xsd`, `DeclaracionInformativa172.xsd` y respuesta XSD; fuente estructurada parseable. |
| 173 | Modelo 173. Declaracion informativa sobre operaciones con monedas virtuales. | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI54/Esquemas173.zip | ZIP with WSDL/XSD | STATUS-A | ZIP oficial contiene `DDIIModelo173.wsdl`, `Declaracion173.xsd`, `DeclaracionInformativa173.xsd` y respuesta XSD; fuente estructurada parseable. |
| 179 | Modelo 179. Cesion de uso de viviendas con fines turisticos. | https://sede.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/ddii/enol/ws/DeclaracionInformativa.xsd | Direct XSD | STATUS-A | M-03 localizo XSD oficial directo enlazado desde documentacion AEAT; parser carga 47 campos XML oficiales. |
| 186 | Modelo 186. Informacion relativa a nacimientos y defunciones. | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI06.shtml | HTML procedure | STATUS-B | Declaracion informativa con procedimiento HTML y normativa, sin diseño de registro especifico ni casillas estructuradas en recursos activos. |
| 206 | Modelo 206. IS/IRNR. Documento de ingreso o devolucion. (Modelo 200 y 206). | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GE04.shtml | HTML procedure tied to model 200 | STATUS-B | AEAT agrupa `Modelo 200 y 206`; el 206 es documento de ingreso/devolucion, no diseño independiente de casillas. |
| 221 | Modelo 221. Prestacion patrimonial por conversion de activos por impuesto diferido. | https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/impuesto-sobre-sociedades/modelo-221-prest_____to-exigible-frente-tributaria_/instrucciones.html | HTML instructions + dynamic endpoint | STATUS-D | Hay instrucciones HTML y endpoint `.zul`, pero no fuente estructurada de casillas; parsear requeriria contrato de formulario. |
| 228 | Modelo 228. Solicitud devolucion por exencion reinversion vivienda habitual. | https://www1.agenciatributaria.gob.es/wlpl/SCEJ-MANT/CONSUL/index.zul?MODELO=228&EJERCICIO=0 | AEAT dynamic endpoint + PDF instructions | STATUS-D | La fuente principal es endpoint dinamico; los PDFs son FAQ/instrucciones, no diseño de campos. |
| 230 | Modelo 230. IRPF/IRNR. Gravamen especial sobre premios de loterias. | https://www1.agenciatributaria.gob.es/wlpl/PAMW-M230/index.zul | AEAT dynamic endpoint | STATUS-D | Aplicacion `.zul` dinamica; no hay diseño de registro especifico parseable en recursos activos. |
| 231 | Modelo 231. Informacion pais por pais (CBC/DAC4). | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI41/WS/231_XSD-2.0_WSDL-2-0-1.zip | ZIP with WSDL/XSD | STATUS-A | M-03 localizo ZIP oficial de servicio web; parser carga 59 campos XML oficiales. |
| 233 | Modelo 233. Gastos en guarderias o centros de educacion infantil autorizados. | https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/declaraciones-informativas-ayuda-tecnica/modelos-199-282/modelo-233.html | HTML technical help | STATUS-E | Ayuda tecnica HTML especifica; posible fuente de formato, pero no soportada por parser actual. |
| 234 | Modelo 234. Mecanismos transfronterizos. | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI46-GI47-GI48/Ejemplos_XML_M234_235_236_Manual.zip | ZIP with XML examples | STATUS-D | M-03 confirma que el ZIP oficial contiene ejemplos XML, no XSD/contrato completo; no se parsea para evitar campos inventados. |
| 235 | Modelo 235. Actualizacion de mecanismos transfronterizos comercializables. | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI46-GI47-GI48/Ejemplos_XML_M234_235_236_Manual.zip | ZIP with XML examples | STATUS-D | Misma fuente que M234; ejemplos XML insuficientes para afirmar completitud. |
| 236 | Modelo 236. Utilizacion de determinados mecanismos transfronterizos. | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI46-GI47-GI48/Ejemplos_XML_M234_235_236_Manual.zip | ZIP with XML examples | STATUS-D | Misma fuente que M234; ejemplos XML insuficientes para afirmar completitud. |
| 238 | Modelo 238. Operadores de plataformas. | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI52/WS/238_XSD-V1.0_WSDL-V1.0.zip | ZIP with WSDL/XSD | STATUS-A | M-03 localizo ZIP oficial de servicio web; parser carga 153 campos XML oficiales. |
| 239 | Modelo 239. Mecanismos de planificacion fiscal AMAC. | https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI57.shtml | HTML procedure / redirected form | STATUS-D | Recursos apuntan a procedimiento y formulario indirecto; no hay diseño estructurado ni esquema localizado. |
| 240 | Modelo 240. Comunicacion entidad declarante Impuesto Complementario. | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI60/Servicio_Web/Modelo_240_Comunicacion_Declarante_XSD_WSDL.zip | ZIP with WSDL/XSD | STATUS-A | M-03 localizo ZIP oficial de servicio web; parser carga 36 campos XML oficiales. |
| 241 | Modelo 241. Declaracion informativa Impuesto Complementario. | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI59/Servicio_Web/Modelo_241_GIR_Globe_-_XSD_V1_1-WSDL_1_1.zip | ZIP with WSDL/XSD | STATUS-A | M-03 localizo ZIP oficial de servicio web; parser carga 403 campos XML oficiales. |
| 247 | Modelo 247. IRNR. Comunicacion desplazamiento al extranjero. | https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/impuesto-sobre-renta-no-residentes/modelo-247-irnr______njero-efectuada-trabajadores-ajena_/descarga-modelo.html | HTML form/download | STATUS-B | Comunicacion descargable sin diseño de registro estructurado en recursos activos. |
| 290 | Modelo 290. FATCA. Cuentas financieras de determinadas personas estadounidenses. | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI38/Ayuda/XSD_WSDL/290_XSD_2.0_WSDL_2.1.1.zip | ZIP with WSDL/XSD | STATUS-A | M-03 localizo ZIP oficial FATCA; parser carga 152 campos XML oficiales. El contrato MCP sigue `parcial` porque no prueba obligatoriedad ni completitud operativa por supuesto. |
| 294 | Modelo 294. Clientes perceptores de beneficios distribuidos por IIC espanolas. | https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_200_299/archivos/294_EHA_1674_2006.pdf | PDF schematic design | STATUS-D | PDF oficial es esquema visual de posiciones; el texto extraido no contiene tabla determinista de campos y no debe parsearse por heuristica. |
| 295 | Modelo 295. Clientes con posicion inversora en IIC espanolas. | https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_200_299/archivos/295_EHA_1674_2006.pdf | PDF schematic design | STATUS-D | PDF oficial es esquema visual de posiciones; el texto extraido no contiene tabla determinista de campos y no debe parsearse por heuristica. |

## Resumen M-00

| status | modelos | accion siguiente |
|---|---|---|
| STATUS-A | 172, 173, 179, 231, 238, 240, 241, 290 | M-02/M-03 completados: parser ZIP/direct XSD implementado en `aeat_current_designs.py`; campos XML oficiales cargados como `diseno_registro_xsd_campo`. |
| STATUS-B | 102, 146, 147, 186, 206, 247 | Marcar como `no-casillas-expected` solo cuando el contrato DB/API soporte ese valor real; no inventar casillas. |
| STATUS-D | 121, 136, 140, 143, 150, 221, 228, 230, 234, 235, 236, 239, 294, 295 | Documentar bloqueo; no cargar hasta tener Playwright/contrato endpoint, XSD oficial o parser fiable. |
| STATUS-E | 233 | Sigue pendiente: ayuda tecnica indica plantilla/fichero, pero no se localizo URL oficial no autenticada y determinista del contrato completo. |

## Resultado M-02

`172` y `173` siguen clasificados como `STATUS-A`, pero el dato cargado es inventario oficial XML/XSD de presentacion telematica, no casillas visuales numeradas. El worker `aeat_current_designs.py` parsea exclusivamente `DeclaracionInformativa{codigo}.xsd` dentro de los ZIP oficiales AEAT y omite `RespuestaDeclaracion*.xsd` y wrappers.

| codigo | source_url | campos cargados | tipo_casilla | evidencia |
|---|---|---:|---|---|
| 172 | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI53/Esquemas172.zip | 35 | `diseno_registro_xsd_campo` | XPath + fuente XSD + tipo XSD + `minOccurs`/`maxOccurs` en `modelo_casilla.descripcion`. |
| 173 | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI54/Esquemas173.zip | 45 | `diseno_registro_xsd_campo` | XPath + fuente XSD + tipo XSD + `minOccurs`/`maxOccurs` en `modelo_casilla.descripcion`. |

Verificacion VPS M-02: `cron-aeat-current-daily` cargo `xsd_fields=80`, `parse_errors=0`; SQL productivo devolvio `172 casillas=35` y `173 casillas=45`; API `/v1/modelos/172` y `/v1/modelos/173` expone esos campos; `mcp_validation_suite` queda `ok=true`.

## Resultado M-03

M-03 resolvio los `STATUS-E` automatizables mediante fuentes oficiales AEAT directas o ZIP con WSDL/XSD. Se descartan ejemplos XML como fuente de verdad porque no prueban contrato completo.

| codigo | source_url | campos cargados | tipo_casilla | contrato MCP |
|---|---|---:|---|---|
| 179 | https://sede.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/ddii/enol/ws/DeclaracionInformativa.xsd | 47 | `diseno_registro_xsd_campo` | `verified=false`, `completeness=parcial` |
| 231 | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI41/WS/231_XSD-2.0_WSDL-2-0-1.zip | 59 | `diseno_registro_xsd_campo` | `verified=false`, `completeness=parcial` |
| 238 | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI52/WS/238_XSD-V1.0_WSDL-V1.0.zip | 153 | `diseno_registro_xsd_campo` | `verified=false`, `completeness=parcial` |
| 240 | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI60/Servicio_Web/Modelo_240_Comunicacion_Declarante_XSD_WSDL.zip | 36 | `diseno_registro_xsd_campo` | `verified=false`, `completeness=parcial` |
| 241 | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI59/Servicio_Web/Modelo_241_GIR_Globe_-_XSD_V1_1-WSDL_1_1.zip | 403 | `diseno_registro_xsd_campo` | `verified=false`, `completeness=parcial` |
| 290 | https://sede.agenciatributaria.gob.es/static_files/Sede/Procedimiento_ayuda/GI38/Ayuda/XSD_WSDL/290_XSD_2.0_WSDL_2.1.1.zip | 152 | `diseno_registro_xsd_campo` | `verified=false`, `completeness=parcial` |

Verificacion VPS M-03: `cron-aeat-current-daily` cargo `xsd_fields=638`, `parse_errors=0`; SQL productivo devolvio `179=47`, `231=59`, `238=153`, `240=36`, `241=403`, `290=152`; API `/v1/modelos/{179,231,238,240,241,290}` expone esos campos con trazabilidad XSD.

## Evidencia usada

- DB productiva via Docker Compose: `aeat_modelo`, `modelo_campana`, `modelo_recurso`, `modelo_casilla`.
- AEAT ZIP oficial inspeccionado para `172`: contiene `DDIIModelo172.wsdl`, `Declaracion172.xsd`, `DeclaracionInformativa172.xsd`, `RespuestaDeclaracion172.xsd`.
- AEAT ZIP oficial inspeccionado para `173`: contiene `DDIIModelo173.wsdl`, `Declaracion173.xsd`, `DeclaracionInformativa173.xsd`, `RespuestaDeclaracion173.xsd`.
- AEAT ZIP oficial inspeccionado para `234/235/236`: contiene ejemplos XML, no XSD completo observado.
- Probes HTML oficiales: procedimientos AEAT `G229`, `G616`, `GE04`, instrucciones `221` y `240`.

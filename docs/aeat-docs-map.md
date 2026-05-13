# AEAT Full Documentation Coverage Map

Estado: D-00 completado. Este mapa identifica fuentes oficiales AEAT para los modelos prioritarios antes de tocar parsers o datos.

Fuentes indice revisadas:

- https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro/modelos-100-199.html
- https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro/modelos-200-299.html
- https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro/modelos-300-399.html

Fuentes tecnicas adicionales revisadas cuando el modelo no aparece en las paginas de diseno o tiene presentacion por servicio web:

- Modelo 289: pagina de ayuda de presentacion y pagina de Web Service CRS/DAC2.
- Modelo 290: pagina de Web Service FATCA y ZIP oficial ya usado en la auditoria AEAT 29.
- Modelo 296: paginas AEAT de presentacion por formulario y por fichero.

Regla D-00: `STATUS-A` significa fuente oficial determinista candidata a carga; no implica que el modelo deba marcarse `verified=true` hasta que el parser cargue campos, claves, notas de formato y trazabilidad suficiente. `STATUS-D` significa que la fuente existe pero no es segura para carga automatica sin contrato adicional.

| codigo | formato | url | status | reason |
|---|---|---|---|---|
| 100 | XSD + diccionarios properties | https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_100_199/Renta2025.xsd | STATUS-A | La pagina 100-199 publica XSD 2025 y diccionarios oficiales; D-08 debe verificar procedencia y trazabilidad de las casillas ya cargadas. |
| 111 | XLS | https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_100_199/archivos/dr111e16v18.xls | STATUS-A | Diseno de registro en hoja Excel oficial; parser XLS/XLSX aplicable. |
| 115 | XLS | https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_100_199/archivos/DR115e15v13.xls | STATUS-A | Diseno de registro en hoja Excel oficial; parser XLS/XLSX aplicable. |
| 123 | XLS | https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_100_199/archivos_24/DR123e24.xls | STATUS-A | Diseno de registro 2024 y siguientes en Excel oficial; gap confirmado frente a respuestas que aun no pueden dar detalle completo. |
| 124 | XLSX | https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_100_199/archivos_20/124v01e2020_v1.07.xlsx | STATUS-A | Diseno de registro en Excel oficial; parser XLSX aplicable. |
| 187 | PDF tabla logica | https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_100_199/DR_Modelo_187_2022.pdf | STATUS-A | El texto extraido contiene `TIPO DE REGISTRO`, `POSICIONES` y `NATURALEZA`; PDF de diseno logico, no layout visual. D-05 debe validar parser PDF. |
| 193 | PDF tabla logica | https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_100_199/DR_Modelo_193_2025.pdf | STATUS-A | PDF oficial 2025 con tabla de diseno de registro; prioritario para capital mobiliario. |
| 196 | PDF tabla logica | https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_100_199/archivos_23/DR_Mod_196_2023.pdf | STATUS-A | PDF oficial con tabla de diseno de registro; ya tenia baseline conocida, D-12 debe reconciliar trazabilidad si falta. |
| 198 | PDF tabla logica | https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_100_199/DR_Modelo_198_2024.pdf | STATUS-A | PDF oficial 2024 con posiciones y naturaleza; modelo principal para operaciones con activos financieros y valores mobiliarios. |
| 200 | XLS | https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_200_299/archivos_25/DR200e25.xls | STATUS-A | Diseno de registro IS 2025 en Excel oficial; D-09 debe verificar cobertura y source_url de lo ya cargado. |
| 216 | XLSX | https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_200_299/archivos_24/216e2024.xlsx | STATUS-A | Diseno oficial 2024 y siguientes; gap prioritario para IRNR retenciones de no residentes. |
| 289 | ZIP XSD/WSDL + manual tecnico PDF | https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/declaraciones-informativas/modelo-289-decla_____ras-ambito-asistencia-mutua/informacion-sobre-presentacion-mediante-web-service.html | STATUS-A | La ayuda tecnica oficial publica esquema XSD 2.0/WSDL 2.0.1 y manual CRS/DAC2; no aparece en el indice 200-299, pero la fuente oficial es determinista. |
| 290 | ZIP XSD/WSDL + manual tecnico PDF | https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/declaraciones-informativas/modelo-290-decla_____s-determinadas-personas-fatca_/informacion-sobre-presentacion-mediante-web-service.html | STATUS-A | Fuente oficial FATCA con XSD 2.0/WSDL 2.1.1. Ya hay 152 campos XSD cargados; mantiene contrato parcial para no afirmar procedimiento completo. |
| 296 | PDF tabla logica | https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_200_299/archivos_24/DR_296_2024.pdf | STATUS-A | PDF oficial 2024 con `Tipo 1`, `Tipo 2`, `POSICIONES` y `NATURALEZA`; D-01 debe sustituir datos semilla/parciales por campos completos. |
| 303 | XLSX | https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro/DR_300_399/archivos_26/DR303e26v101.xlsx | STATUS-A | Modelo fuera del rango 100-299, pero prioritario. La pagina 300-399 publica Excel 2026 y siguientes; D-10 debe verificar o recargar desde fuente oficial. |

## Brechas Confirmadas Para Carga

| codigo | brecha | accion |
|---|---|---|
| 296 | Las respuestas actuales muestran cobertura parcial y ausencia de instrucciones completas pese a existir PDF oficial de diseno logico. | D-01: parsear PDF 2024, cargar campos tipo 1/tipo 2, claves y notas de formato si aparecen. |
| 216 | Existe XLSX oficial 2024 y siguientes; debe cubrir mejor las respuestas sobre retenciones IRNR. | D-02: parser XLSX y carga completa. |
| 193 | Existe PDF oficial 2025; relevante para capital mobiliario. | D-03: parser PDF de tabla logica y carga de registros/claves. |
| 198 | Existe PDF oficial 2024; relevante para sociedades de valores y transmisiones. | D-04: parser PDF y carga de campos/claves. |
| 187 | Existe PDF oficial de diseno logico; relevante para IIC. | D-05: parser PDF y carga segura. |
| 123, 124 | Existen XLS/XLSX oficiales. | D-06: parser spreadsheet y carga/reconciliacion. |
| 289 | Existe ZIP XSD/WSDL y manual CRS/DAC2 en ayuda tecnica oficial. | D-07: cargar XSD si el contrato es determinista; mantener parcial si solo prueba mensaje tecnico. |
| 111, 115, 200, 303 | Existen hojas oficiales; se deben verificar source_url, campana y trazabilidad de lo ya cargado. | D-09 a D-12: verificar o recargar sin mezclar semilla. |

## Fuentes De Ayuda Tecnica Localizadas

| codigo | fuente tecnica | uso |
|---|---|---|
| 289 | https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/declaraciones-informativas-ayuda-tecnica/modelos-199-289/modelo-289.html | Procedimiento formulario 2026; no sustituye al XSD/WSDL para campos. |
| 289 | https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/declaraciones-informativas/modelo-289-decla_____ras-ambito-asistencia-mutua/informacion-sobre-presentacion-mediante-web-service.html | Fuente de XSD/WSDL y manual tecnico. |
| 290 | https://sede.agenciatributaria.gob.es/Sede/todas-gestiones/impuestos-tasas/declaraciones-informativas/modelo-290-decla_____s-determinadas-personas-fatca_/informacion-sobre-presentacion-mediante-web-service.html | Fuente de XSD/WSDL y manual tecnico FATCA. |
| 296 | https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/declaraciones-informativas-ayuda-tecnica/modelos-291-347/modelo-296-formulario.html | Ayuda de formulario; util para procedimiento, no para tabla de campos. |
| 296 | https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/declaraciones-informativas-ayuda-tecnica/modelos-291-347/modelo-296-fichero.html | Ayuda de fichero; enlaza a disenos 200-299. |

## Siguiente Historia

D-01 debe centrarse solo en el modelo 296. Antes de cargar, comprobar schema real con `\d modelo_casilla` en Docker y decidir si la trazabilidad por campo vive en `modelo_casilla.descripcion`, `modelo_recurso`, `source_revision` o requiere migracion. No marcar `verified=true` por el simple hecho de tener mas campos; solo hacerlo si el contrato de completitud definido para el modelo queda satisfecho.

## Resultado D-12

Todos los modelos prioritarios `STATUS-A` del mapa tienen campos oficiales cargados y trazables en produccion. Los modelos que siguen con contrato API `parcial` lo hacen por ausencia de instrucciones completas, metadata operativa o reglas de aplicabilidad estructuradas, no por ausencia de diseno oficial.

| codigo | casillas produccion | fuente cargada | contrato API |
|---|---:|---|---|
| 100 | 2521 | XSD + diccionarios AEAT 2025 | `verified=true`, `completa` |
| 111 | 63 | XLS AEAT | `verified=false`, `parcial` |
| 115 | 37 | XLS AEAT | `verified=false`, `parcial` |
| 123 | 44 | XLS AEAT | `verified=false`, `parcial` |
| 124 | 39 | XLSX AEAT | `verified=false`, `parcial` |
| 187 | 50 | PDF logico AEAT | `verified=false`, `parcial` |
| 193 | 71 | PDF logico AEAT | `verified=false`, `parcial` |
| 196 | 62 | PDF logico AEAT | `verified=false`, `parcial` |
| 198 | 72 | PDF logico AEAT | `verified=false`, `parcial` |
| 200 | 6807 | XLS + anexos AEAT | `verified=false`, `parcial` |
| 216 | 47 | XLSX AEAT | `verified=false`, `parcial` |
| 289 | 134 | ZIP XSD/WSDL AEAT | `verified=false`, `parcial` |
| 290 | 152 | ZIP XSD/WSDL AEAT | `verified=false`, `parcial` |
| 296 | 124 | PDF logico AEAT | `verified=false`, `parcial` |
| 303 | 432 | XLSX AEAT 300-399 | `verified=false`, `parcial` |

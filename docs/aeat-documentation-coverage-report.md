# AEAT Documentation Coverage Report

Estado: D-13 completado para el sprint `esdata-aeat-full-documentation`.

Fecha de corte: 2026-05-13.

## Resumen Ejecutivo

El sprint amplió la cobertura documental oficial AEAT donde existían fuentes deterministas publicadas por la AEAT. La regla aplicada fue conservadora: cargar campos oficiales de diseño de registro no convierte por sí solo un modelo en guía completa de cumplimentación ni prueba obligatoriedad por supuesto.

Resultado productivo para modelos numéricos `100-299`:

| metrica | valor |
|---|---:|
| Modelos 100-299 inventariados | 88 |
| Modelos con casillas/campos oficiales cargados | 65 |
| Modelos con cero casillas activas | 23 |
| Modelos prioritarios STATUS-A cubiertos con fuente oficial | 15/15 |

## Contrato De Verdad Aplicado

| contrato | significado operativo |
|---|---|
| `verified=true`, `completa` | Respuesta autoritativa para el alcance cargado. |
| `verified=false`, `parcial` | Evidencia limitada: hay fuente/campos oficiales parciales, pero no instrucciones completas ni reglas de aplicabilidad estructuradas. |
| `verified=true`, `no-casillas-expected` | La ausencia de casillas estructuradas esta verificada para ese tipo de formulario/comunicacion. |
| `deprecated` | Modelo no vigente o reemplazado; no debe tratarse como modelo actual. |
| `STATUS-D` | Bloqueado de forma honesta: fuente dinamica, visual, ejemplo XML o no determinista. |
| `STATUS-E` | Fuente pendiente de localizar o automatizar con contrato determinista. |

## Modelos Prioritarios Cargados

Todos los modelos prioritarios definidos en `docs/aeat-docs-map.md` tienen ya campos oficiales trazables desde fuentes AEAT.

| codigo | casillas produccion | fuente oficial cargada | contrato API/MCP |
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

`303` esta fuera del rango `100-299`, pero se incluyo por prioridad operativa y porque la AEAT publica su diseno oficial en la pagina `300-399`.

## Modelos 100-299 Sin Casillas Activas

Los 23 modelos sin casillas activas no quedan como huecos silenciosos. Cada uno tiene una razon documental o un estado de bloqueo.

| codigo | estado | razon |
|---|---|---|
| 102 | `no-casillas-expected` | Segundo plazo/fraccionamiento IRPF; formulario operativo sin diseno de registro estructurado localizado. |
| 110 | `deprecated/legacy` | Modelo legacy reemplazado operativamente por modelos posteriores; no se trata como fuente activa con casillas. |
| 121 | `STATUS-D` | Fuente dinamica/formulario o ayuda no determinista; no se carga sin contrato oficial parseable. |
| 136 | `STATUS-D` | Fuente dinamica/formulario o ayuda no determinista. |
| 140 | `STATUS-D` | Fuente dinamica/formulario o ayuda no determinista. |
| 143 | `STATUS-D` | Fuente dinamica/formulario o ayuda no determinista. |
| 146 | `no-casillas-expected` | Comunicacion/formulario sin diseno estructurado localizado. |
| 147 | `no-casillas-expected` | Comunicacion/formulario sin diseno estructurado localizado. |
| 150 | `STATUS-D` | Fuente dinamica/formulario o PDF no determinista. |
| 186 | `no-casillas-expected` | Declaracion/comunicacion sin casillas estructuradas por diseno localizado. |
| 206 | `no-casillas-expected` | Modelo operativo sin diseno estructurado determinista localizado. |
| 221 | `STATUS-D` | Fuente dinamica/formulario o ayuda no determinista. |
| 228 | `STATUS-D` | Fuente dinamica/formulario o ayuda no determinista. |
| 230 | `STATUS-D` | Fuente dinamica/formulario o ayuda no determinista. |
| 233 | `STATUS-E` | Pendiente de localizar contrato/plantilla oficial determinista. |
| 234 | `STATUS-D` | Solo ejemplos XML localizados; no se cargan ejemplos como definicion de campos. |
| 235 | `STATUS-D` | Solo ejemplos XML localizados; no se cargan ejemplos como definicion de campos. |
| 236 | `STATUS-D` | Solo ejemplos XML localizados; no se cargan ejemplos como definicion de campos. |
| 239 | `STATUS-D` | Fuente dinamica/formulario o ayuda no determinista. |
| 247 | `no-casillas-expected` | Comunicacion/formulario sin diseno estructurado localizado. |
| 294 | `STATUS-D` | Fuente dinamica/formulario o ayuda no determinista. |
| 295 | `STATUS-D` | Fuente dinamica/formulario o ayuda no determinista. |
| 299 | `legacy/placeholder` | Registro sin diseno activo independiente cargable en el corpus actual. |

## Implicacion Para Respuestas MCP

El MCP debe responder con mas precision en modelos como `296`, `198`, `193`, `216`, `289` y `290` porque ya dispone de campos oficiales completos o mucho mas amplios que la semilla inicial. Aun asi, salvo `100`, la respuesta correcta sigue siendo `evidence_limited` cuando el usuario pide instrucciones completas, obligatoriedad o aplicabilidad por caso.

Ejemplo: para el Modelo 296, ESData puede listar campos de cabecera, registros, claves y posiciones cargadas desde el PDF oficial. No debe afirmar que sabe cumplimentar todos los supuestos ni que un campo concreto sea obligatorio si esa regla no esta estructurada en la evidencia.

## Verificacion D-13

Comandos/evidencia usados:

- SQL productivo: modelos `100-299` => `total=88`, `loaded=65`, `zero=23`.
- `docs/aeat-docs-map.md` actualizado con tabla final D-12.
- `mcp_validation_suite.py --read-only --base-url http://127.0.0.1:8000` en VPS => `ok=true`.
- `mcp_deep_contract_audit.py --base-url http://api:8000` en contenedor API con repo montado en solo lectura => `ok=true`.

Resultado: D-13 pasa. Las dos suites validan el contrato y los modelos sin casillas quedan documentados con razon explicita, no como ausencia silenciosa.

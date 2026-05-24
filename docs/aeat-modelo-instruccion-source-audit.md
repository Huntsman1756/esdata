# AEAT Modelo Instruccion Source Audit

## Estado

Auditoria read-only de `modelo_instruccion` legacy sin `source_url`.

Resultado: no queda deuda de filas con `source_url` y evidencia incompleta en
metadata auxiliar AEAT. La deuda residual de instrucciones esta en textos
resumidos legacy sin fuente propia por fila.

## Resultado global

| Tabla | Total | Sin source_url | Normalizadas | URL incompleta |
| --- | ---: | ---: | ---: | ---: |
| `modelo_instruccion` | 70 | 17 | 53 | 0 |
| `modelo_clave` | 179 | 20 | 159 | 0 |
| `modelo_regla_inclusion` | 30 | 0 | 30 | 0 |

## Filas `modelo_instruccion` sin fuente por fila

| Modelo | Filas | Diagnostico |
| --- | ---: | --- |
| `100` | 4 | Textos resumen sobre declaracion anual, obligados, plazo y pasos de cumplimentacion. No hay coincidencia literal con fuente oficial activa. |
| `111` | 4 | Textos resumen sobre retenciones, obligados, plazo y pasos de cumplimentacion. Las fuentes oficiales activas comparten terminos, pero no prueban el texto legacy por fila. |
| `036` | 3 | Textos resumen sobre declaracion censal, obligados y plazo. No hay fuente oficial por fila que soporte la redaccion exacta. |
| `347` | 3 | Textos resumen sobre operaciones con terceros, obligados y plazo. No hay coincidencia literal con instrucciones/ficha activa. |
| `349` | 3 | Textos resumen sobre operaciones intracomunitarias, obligados y plazo. Hay solapamiento tematico con instrucciones/ficha, pero no trazabilidad textual suficiente por fila. |

## Decision

No se normaliza ninguna fila `modelo_instruccion` en este bloque.

La presencia de recursos oficiales activos para un modelo no permite rellenar
`source_url`, `source_hash` y `capture_date` en instrucciones legacy si el texto
de la fila es un resumen editorial o una reformulacion no trazable.

## Implicaciones

- `obligacion_perfil` no se toca.
- No se modifica `safe_to_answer`.
- No se modifica `verified`.
- No se modifica `completeness` funcional.
- Las instrucciones legacy sin fuente deben tratarse como deuda documental hasta
  localizar una fuente deterministica o reemplazarlas por filas oficiales
  verificables.

## Siguiente accion

No abrir migracion de recuperacion para estas instrucciones. Si se quiere
mejorar el contrato, el siguiente bloque debe reemplazar textos legacy por
instrucciones oficiales verificables, no asignarles evidencia por proximidad.

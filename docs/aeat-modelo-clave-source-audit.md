# AEAT Modelo Clave Source Audit

## Estado

Auditoria read-only de `modelo_clave` tras el cierre de evidencia auxiliar del
Modelo 289.

Resultado: no queda deuda de filas con `source_url` y evidencia incompleta en
metadata auxiliar AEAT. La deuda residual esta en filas legacy sin `source_url`
propio.

## Resultado global

| Tabla | Total | Sin source_url | Normalizadas | URL incompleta |
| --- | ---: | ---: | ---: | ---: |
| `modelo_clave` | 179 | 20 | 159 | 0 |
| `modelo_instruccion` | 70 | 17 | 53 | 0 |
| `modelo_regla_inclusion` | 30 | 0 | 30 | 0 |

No hay filas auxiliares con `source_url` presente y `source_hash` o
`capture_date` ausente.

## Filas `modelo_clave` sin fuente por fila

| Modelo | Filas | Diagnostico |
| --- | ---: | --- |
| `111` | 5 | Las instrucciones oficiales mencionan categorias de renta, pero no prueban los codigos legacy `01`-`05` como claves oficiales por fila. |
| `190` | 4 | Las instrucciones oficiales mencionan categorias de percepcion, pero los codigos legacy `A`-`D` no quedan trazados de forma suficiente; en particular, premios y ganancias no se corresponden con una tabla de claves `C`/`D` en el texto auditado. |
| `196` | 3 | La fuente oficial activa no prueba las claves legacy `A` dividendos, `B` intereses y `C` transmision. |
| `303` | 8 | Las instrucciones oficiales mencionan regimenes o casillas, pero no prueban los codigos legacy `0`-`7` como claves oficiales normalizables. |

## Decision

No se normaliza ninguna fila `modelo_clave` en este bloque.

La existencia de un recurso oficial activo para el modelo no basta para cargar
`source_url`, `source_hash` y `capture_date` en cada clave. Cada fila debe estar
trazada contra una tabla, instruccion o diseno oficial que soporte el codigo y
la descripcion concretos.

## Implicaciones

- `obligacion_perfil` no se toca.
- No se modifica `safe_to_answer`.
- No se modifica `verified`.
- No se modifica `completeness` funcional.
- Las claves legacy sin fuente deben tratarse como deuda documental hasta
  localizar una fuente deterministica por fila.

## Siguiente accion

No abrir migracion de recuperacion para estas claves hasta localizar una fuente
oficial deterministica. El candidato real no es un modelo concreto, sino una
fuente de claves: instrucciones o diseno de registro que contenga codigo y
descripcion de cada clave.

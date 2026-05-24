# Obligacion perfil global fail-closed

Fecha: 2026-05-24

## Objetivo

Sanear `obligacion_perfil` como superficie global de obligaciones por perfil.
Una obligacion no puede exponerse como verificada ni segura si carece de
`source_hash` o `capture_date`, aunque tenga URL oficial, articulo o flags
legacy.

## Auditoria previa

Produccion mostraba 157 filas con `safe_to_answer=true` y `verified=true` sin
`source_hash`. Todas tenian `source_url` y `capture_date`; el hueco era la
evidencia hash normalizada.

| Grupo | Filas inseguras |
| --- | ---: |
| Sin `modelo_aeat` | 137 |
| `111` | 6 |
| `115` | 6 |
| `289` | 4 |
| `290` | 3 |
| `196` | 1 |

`216` queda como referencia positiva: sus obligaciones seguras tienen URL,
hash y fecha de captura.

## Contrato

- `safe_to_answer=true` requiere `source_url`, `source_hash`,
  `capture_date`, `verified=true` y `completeness='completa'`.
- `verified=true` no debe exponerse si falta `source_hash` o `capture_date`.
- Si falta evidencia normalizada, la obligacion queda `partial`/`parcial`,
  `verified=false`, `safe_to_answer=false` y `review_required=true`.
- Un articulo o modelo asociado no sustituye la evidencia hash/captura.
- Recuperar una obligacion como segura debe hacerse cargando evidencia real,
  no restaurando flags legacy.

## Cambios

- `GET /v1/modelos/aeat/{codigo}` degrada `obligation_context[].verified` y
  `completeness` cuando falta evidencia normalizada.
- `GET /v1/norma/{codigo}` incluye `source_hash`/`capture_date` en
  `obligaciones_referenciadas` y degrada obligaciones sin evidencia.
- Alembic `20260524_0095_obligacion_perfil_global_fail_closed` actualiza
  globalmente las filas sin `source_hash` o `capture_date`.

## Recuperacion futura

La auditoria localizo hashes candidatos para algunos subconjuntos:

- `111`, `115` y `196`: posible recuperacion desde `modelo_recurso`.
- `290`: posible recuperacion desde `source_revision`.
- `289` y las obligaciones regulatorias sin modelo no tienen hash emparejado
  en la auditoria actual.

Estas recuperaciones deben abrirse como bloques separados y solo promover filas
cuando la relacion entre obligacion y fuente sea trazable.

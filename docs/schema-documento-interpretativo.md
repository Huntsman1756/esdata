# documento_interpretativo schema

Fecha: 2026-05-19

## Columnas

| columna | tipo | nullable |
|---|---|---|
| id | integer | NO |
| tipo_documento | text | NO |
| organismo_emisor | text | NO |
| jurisdiccion | text | NO |
| tipo_fuente | text | NO |
| ambito | text | NO |
| referencia | text | NO |
| fecha | date | NO |
| titulo | text | YES |
| texto | text | NO |
| url_fuente | text | YES |
| search_vector | tsvector | YES |
| numero_circular | text | YES |
| fecha_publicacion | text | YES |
| referencia_boe | text | YES |
| estado_vigencia | text | YES |
| ambito_tematico | text | YES |
| regulacion_relacionada | text | YES |
| embedding_model_name | text | YES |
| content_hash | text | YES |
| row_completeness | text | NO |
| row_provenance | text | NO |
| metadata | jsonb | YES |
| sujeto_obligado | text[] | YES |

## Decision sujeto_obligado

Sprint L usa una columna queryable `sujeto_obligado text[]` en `documento_interpretativo`.

Razon: la aplicabilidad CNMV es multi-perfil y se consulta de forma operacional por endpoint (`/v1/cnmv/perfil/{perfil_codigo}`). Guardarlo solo en `metadata` obligaria a filtros JSONB mas fragiles y menos legibles. La columna se anade de forma aditiva; `metadata` sigue disponible para metadatos especificos de fuente.

## cnmv_obligation_link

`cnmv_obligation_link` relaciona un documento CNMV con una clasificacion operativa de obligacion:

| columna | uso |
|---|---|
| documento_referencia | referencia de `documento_interpretativo.referencia` |
| tipo_obligacion | familia operativa (`remision_informacion`, `control_interno`, `modelo_normalizado_esi`, etc.) |
| nota | texto explicativo |

La tabla no apunta a `obligacion_perfil.id`; es una relacion documental CNMV -> tipo de obligacion. Cuando Sprint L crea obligaciones de perfil desde circulares CNMV, la trazabilidad primaria sigue en `obligacion_fuente`; `cnmv_obligation_link` mantiene la clasificacion documental.

## Query por perfil

Patron canonico para documentos CNMV aplicables a un perfil:

```sql
SELECT referencia, titulo, tipo_documento, fecha, url_fuente, estado_vigencia, ambito_tematico
FROM documento_interpretativo
WHERE organismo_emisor = 'CNMV'
  AND tipo_fuente = 'cnmv'
  AND sujeto_obligado @> ARRAY['sociedad_valores']::text[]
  AND estado_vigencia <> 'derogada'
ORDER BY fecha DESC, referencia;
```

Los registros oficiales CNMV no se modelan en este sprint; la familia `registros_oficiales` permanece `configured_but_unavailable`.

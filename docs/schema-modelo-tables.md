# Modelo Tables Schema

Source of truth for Sprint J (CRS/Modelo 289). Captured from production on
2026-05-18 using `docker compose exec postgres psql` on the VPS.

## Modelo 289 identifiers

| item | value |
|------|-------|
| aeat_modelo.id | 95 |
| aeat_modelo.codigo | 289 |
| modelo_campana.id | 95 |
| modelo_campana.modelo_id | 95 |
| modelo_campana.campana | 2025 |

Join rule for Sprint J:

- `modelo_campana.modelo_id` joins to `aeat_modelo.id`.
- `modelo_instruccion`, `modelo_regla_inclusion`, `modelo_casilla`,
  `modelo_recurso` use `campana_id`.
- `modelo_trigger_keyword` uses `modelo_id`; it has no `campana_id`.
- `modelo_normativa` uses `modelo_id`; it has no `campana_id`.

## aeat_modelo

| columna | tipo | nullable |
|---------|------|----------|
| id | integer | NO |
| codigo | text | NO |
| nombre | text | NO |
| periodo | text | YES |
| impuesto | text | YES |
| url_info | text | YES |
| created_at | timestamp with time zone | YES |
| embedding_384 | USER-DEFINED | YES |
| embedding_model_name | text | YES |
| content_hash | text | YES |
| activo | boolean | NO |
| url_listado | text | YES |
| slug_portal | text | YES |
| derogado_at | timestamp with time zone | YES |
| updated_at | timestamp with time zone | NO |

## modelo_campana

| columna | tipo | nullable |
|---------|------|----------|
| id | integer | NO |
| modelo_id | integer | NO |
| campana | text | NO |
| version_form | text | YES |
| url_instrucciones | text | YES |
| url_normativa | text | YES |
| url_formato | text | YES |
| activo | boolean | NO |
| creado_at | timestamp with time zone | YES |
| fecha_publicacion_portal | date | YES |
| fecha_actualizacion_portal | date | YES |
| estado_publicacion | text | YES |
| updated_at | timestamp with time zone | NO |

## modelo_casilla

| columna | tipo | nullable |
|---------|------|----------|
| id | integer | NO |
| campana_id | integer | NO |
| codigo | text | NO |
| etiqueta | text | NO |
| descripcion | text | YES |
| tipo_casilla | text | YES |
| pagina | integer | YES |
| orden | integer | YES |
| activa | boolean | NO |
| creado_at | timestamp with time zone | YES |

## modelo_instruccion

| columna | tipo | nullable |
|---------|------|----------|
| id | integer | NO |
| campana_id | integer | NO |
| seccion | text | NO |
| titulo | text | NO |
| contenido | text | NO |
| orden | integer | YES |
| creado_at | timestamp with time zone | YES |
| texto | text | YES |
| casilla_referencia | character varying | YES |
| source_url | text | YES |
| source_hash | character varying | YES |
| capture_date | date | YES |

## modelo_normativa

| columna | tipo | nullable |
|---------|------|----------|
| id | integer | NO |
| modelo_id | integer | NO |
| boe_id | text | YES |
| titulo | text | NO |
| fecha | date | YES |
| url_boe | text | YES |
| resumen | text | YES |
| creado_at | timestamp with time zone | YES |

## modelo_recurso

| columna | tipo | nullable |
|---------|------|----------|
| id | bigint | NO |
| campana_id | integer | NO |
| tipo_recurso | text | NO |
| formato | text | NO |
| url_recurso | text | NO |
| sha256_contenido | text | NO |
| etag | text | YES |
| last_modified | text | YES |
| content_length | bigint | YES |
| fecha_publicacion_recurso | date | YES |
| metadata | jsonb | NO |
| activa | boolean | NO |
| first_seen_at | timestamp with time zone | NO |
| last_seen_at | timestamp with time zone | NO |
| row_completeness | text | NO |
| row_provenance | text | NO |

## modelo_regla_inclusion

| columna | tipo | nullable |
|---------|------|----------|
| id | integer | NO |
| campana_id | integer | NO |
| supuesto | text | NO |
| decision | character varying | NO |
| condicion | text | YES |
| umbral | text | YES |
| fuente_normativa | text | YES |
| source_url | text | NO |
| source_hash | character varying | YES |
| capture_date | date | YES |
| creado_at | timestamp with time zone | YES |

## modelo_trigger_keyword

| columna | tipo | nullable |
|---------|------|----------|
| id | integer | NO |
| modelo_id | integer | NO |
| keyword | character varying | NO |
| dominio | character varying | YES |
| creado_at | timestamp with time zone | YES |

## Sprint J insertion notes

- Do not reference `aeat_modelo_instruccion` or `aeat_modelo_clave`; neither
  table exists in production.
- The earlier diagnostic found `modelo_clave`, but Sprint J J-01 did not require
  it for the accepted insertion surface. Inspect it before using it in a later
  story.
- J-02 verification command in the prompt uses `campana_id` for
  `modelo_normativa`, but production `modelo_normativa` has `modelo_id` instead.
  J-02 must adapt the SQL to the real schema documented here.
- J-05 and J-06 verification commands in the prompt mention fallback columns that
  are not present in production (`campana_id` on `modelo_trigger_keyword`,
  `modelo_id` on `modelo_casilla`). Use the real owner column documented above.

# Spec de expansion de modelos, leyes y organismos

## Objetivo

Checklist reutilizable para ampliar `esdata` sin romper el esquema actual.

## 1. Nuevo modelo AEAT

### Archivos a revisar o crear

- `apps/workers/aeat_models.py`
- `apps/workers/modelos.py`
- `scripts/data/seed_modelos.py`
- `scripts/data/seed_aeat_models.py`
- `scripts/data/seed_modelo_articulo.py`
- `apps/workers/tests/test_aeat_models.py`
- `apps/workers/tests/test_modelos.py`
- `scripts/tests/test_seed_aeat_models.py`
- `scripts/tests/test_seed_modelo_articulo.py`

### Tablas implicadas

- `aeat_modelo`
- `modelo_campana`
- `modelo_campana_operativa`
- `modelo_casilla`
- `modelo_clave`
- `modelo_instruccion`
- `modelo_articulo`
- `modelo_normativa`
- `modelo_formato`

### Pasos

1. Añadir el codigo/nombre/impuesto al catalogo curado.
2. Añadir URLs oficiales de discovery o detalle del modelo.
3. Extender parsing de campañas, casillas, claves e instrucciones.
4. Insertar o actualizar mapeos `modelo_articulo`.
5. Verificar drift entre campañas nuevas y anteriores.
6. Añadir tests de parsing, upsert e idempotencia.

## 2. Nueva ley espanola

### Archivos a revisar o crear

- `apps/workers/boe.py`
- opcional: worker dedicado si la ley necesita enrichment especifico
- `scripts/data/seed_boe.py`
- `apps/workers/tests/test_boe.py`
- `apps/api/routers/legislacion.py`

### Patrón de identificacion

- usar `BOE-A-YYYY-NNNNN` como identificador canonico
- mapear a `norma.codigo` y `norma.boe_id`

### Tablas implicadas

- `norma`
- `articulo`
- `version_articulo`
- `materia`
- `articulo_materia`

### Pasos

1. Añadir la ley a `DEFAULT_NORMAS` y mapas de clasificacion si aplica.
2. Confirmar la URL oficial BOE y el bloque consolidado.
3. Parsear articulos y versiones vigentes.
4. Relacionar articulos con materias o modelos si corresponde.
5. Añadir tests de ingestion y lectura API.

## 3. Nueva regulacion UE

### Archivos a revisar o crear

- `apps/workers/eurlex.py`
- `scripts/data/seed_eurlex.py`
- `apps/workers/tests/test_eurlex.py`
- `apps/api/routers/eurlex.py`

### Patrón de identificacion

- usar `CELEX` como identificador canonico

### Tablas implicadas

- `norma`
- `articulo`
- `version_articulo`
- `source_revision`
- `sync_log`

### Pasos

1. Añadir CELEX al catalogo `EURLEX_NORMAS` o al seed curado.
2. Confirmar discovery por SPARQL o corpus local `corpora/eurlex/`.
3. Verificar parsing de articulos/versiones.
4. Añadir tests de CELEX nuevo y fallback de corpus si aplica.

## 4. Nuevo organismo

### Archivos a crear o clonar

- `apps/workers/<organismo>.py`
- `apps/workers/tests/test_<organismo>.py`
- `scripts/data/seed_<organismo>.py` si hay seed curado
- `apps/api/routers/<organismo>.py` si necesita endpoint dedicado
- docs operativas y de fuente

### Tablas implicadas

- `documento_interpretativo`
- `source_revision`
- `sync_log`
- y tablas extra si requiere versionado o links especificos como `CNMV`

### Pasos

1. Definir `worker_name` y `*_SYNC_INTERVAL_SECONDS`.
2. Definir `*_SEED_URLS` o estrategia de discovery.
3. Implementar fetch, parsing, upsert y `record_revision()` por entidad.
4. Registrar errores en `sync_log`, no swallow silencioso.
5. Añadir endpoint dedicado solo si aporta contrato estable; si no, usar `doctrina` generica.
6. Documentar fuente oficial, conflict key y limitaciones.

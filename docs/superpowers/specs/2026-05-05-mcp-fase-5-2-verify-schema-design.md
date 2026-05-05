# Diseno: MCP Fase 5.2 - Expandir verify_schema.py

## Objetivo

Expandir `scripts/maintenance/verify_schema.py` para que el gate de deploy valide el esquema minimo que exige el runtime actual, no solo la tabla `modelo_campana_operativa`.

La fase sigue siendo deliberadamente estrecha:

- mantiene `verify_schema.py` como comprobacion estructural pequena
- amplia el contrato a tablas y columnas criticas ya usadas por runtime real
- no convierte el script en una auditoria completa del esquema
- deja indices, constraints, semillas y verificaciones de datos para fases posteriores

El objetivo exacto es que el deploy falle si falta alguna tabla o columna imprescindible para el runtime MCP/API/workers ya desplegado, incluso aunque `alembic upgrade head` haya corrido sin una comprobacion semantica minima del esquema final.

## Contexto

El plan MCP fija en `5.2` que toca expandir `verify_schema.py`.

Estado actual confirmado tras `5.1`:

- `scripts/ops/deploy-hetzner.sh` ya ejecuta `alembic upgrade head` y despues `python scripts/maintenance/verify_schema.py`
- `verify_schema.py` solo comprueba hoy `modelo_campana_operativa`
- el runtime actual ya depende de otras superficies de esquema activas en fases recientes:
  - `query_audit_log` con campos de grounding y `response_payload`
  - `dgt_queue` como cola persistente de DGT
  - `documento_interpretativo` con `row_completeness` y `row_provenance`

El hueco real no es que falten migraciones, sino que el gate sigue siendo demasiado estrecho para detectar drift relevante del runtime actual.

## Alcance aprobado

Incluye:

- ampliar `REQUIRED_SCHEMA` en `scripts/maintenance/verify_schema.py`
- mantener `find_schema_issues(...)` como comprobacion de tablas/columnas faltantes
- mantener la semantica de salida del script (`0` OK, `1` drift, `2` falta `DATABASE_URL`)
- anadir tests del script en `scripts/tests/`
- actualizar `docs/master-execution-roadmap.md`
- anadir nota reusable en `docs/operations/agent-notes.md` si emerge una regla clara de deploy/schema gating

No incluye:

- validar indices o constraints
- validar seeds, conteos o presencia de filas
- tocar de nuevo `scripts/ops/deploy-hetzner.sh`
- ampliar el gate a toda tabla historica o auxiliar del repo

## Enfoques considerados

### Opcion 1 - contrato minimo del runtime actual

Ampliar `verify_schema.py` con un conjunto pequeno de tablas y columnas criticas ya usadas por runtime real y por slices MCP recientes.

Ventajas:

- alineado con el objetivo de deploy gating
- cambio pequeno y testeable
- reduce falsos verdes sin volver fragil el script

Inconvenientes:

- el contrato requiere mantenimiento explicito cuando nuevas fases anadan dependencias estructurales reales

### Opcion 2 - comprobacion estructural mixta con indices/constraints

Ademas de tablas/columnas, el script tambien exige algunos indices o constraints clave.

Ventajas:

- mayor cobertura estructural

Inconvenientes:

- mas fragil entre dialectos y entornos de test
- mezcla `5.2` con hardening adicional no necesario para el gate minimo de deploy

### Opcion 3 - auditoria estructural casi completa

Convertir `verify_schema.py` en un verificador mucho mas amplio del esquema del repo.

Ventajas:

- cobertura maxima

Inconvenientes:

- fuera de escala para `5.2`
- alto coste de mantenimiento
- mas propenso a bloquear deploys por drift no critico para el runtime actual

## Decision aprobada

Se aprueba la opcion 1.

`verify_schema.py` se ampliara solo hasta cubrir el contrato minimo del runtime actual que ya usa el deploy Compose y las fases MCP recientes.

## Contrato aprobado

`verify_schema.py` seguira verificando exclusivamente:

- tablas requeridas
- columnas requeridas por tabla

Si falta una tabla, el script debe emitir `missing table: <tabla>`.

Si falta una columna, el script debe emitir `missing column: <tabla>.<columna>`.

No se anaden comprobaciones de:

- filas o seeds
- indices
- constraints
- tipos exactos de columna

## Tablas y columnas cubiertas en 5.2

### `modelo_campana_operativa`

Se mantiene el contrato ya existente:

- `campana_id`
- `categoria_obligado`
- `frecuencia_presentacion`
- `ventana_presentacion`
- `canal_presentacion`
- `obligados_resumen`
- `plazo_resumen`
- `presentacion_resumen`
- `norma_base`
- `nota`
- `actualizado_at`
- `origen_metadato`
- `estado_metadato`

### `query_audit_log`

Se amplia el gate a los campos minimos que el runtime MCP/API usa hoy para auditoria durable y respuesta grounding-aware:

- `entry_id`
- `request_id`
- `path`
- `query_text`
- `retrieved_chunks`
- `response_summary`
- `tool_name`
- `sources`
- `confidence`
- `completeness`
- `verified`
- `grounding_status`
- `prompt_injection_detected`
- `grounding_summary`
- `response_payload`
- `created_at`

Siguen fuera de esta fase columnas no esenciales para el gate minimo aunque existan en runtime, como `user_id`, `model_version` o `config_version`.

### `dgt_queue`

Se amplia el gate a la cola persistente que el worker DGT ya usa como frontera owned por Alembic:

- `worker_name`
- `source_entity_id`
- `dgt_url`
- `status`
- `queued_at`
- `processed_at`

Ademas del set minimo de columnas, el gate debe validar la unicidad requerida por el runtime para `ON CONFLICT (worker_name, source_entity_id)`.

Contrato aprobado en este slice:

- en SQLite/tests se acepta una unique index o un autoindex equivalente que cubra exactamente `worker_name, source_entity_id`
- en Postgres/produccion se acepta una unique constraint o indice unico equivalente sobre esas dos columnas

### `documento_interpretativo`

Se amplia el gate al contrato minimo de row quality introducido por fases recientes:

- `row_completeness`
- `row_provenance`

No se revalida aqui el resto de columnas historicas de la tabla porque el objetivo de `5.2` no es reconstruir todo su esquema, sino asegurar las nuevas dependencias estructurales del runtime actual.

## Runtime aprobado

`scripts/maintenance/verify_schema.py` mantiene su forma actual para columnas/tablas, pero puede introducir un helper pequeno adicional para comprobar la unicidad de `dgt_queue` sin convertirse en un auditor estructural general.

- `normalize_db_url(...)` se conserva
- `find_schema_issues(...)` sigue devolviendo `list[str]`
- `main()` mantiene el contrato de exit codes

Cambios aprobados:

- ampliar `REQUIRED_SCHEMA`
- anadir una comprobacion pequena y focalizada para la unicidad de `dgt_queue(worker_name, source_entity_id)`
- hacer el mensaje de exito mas explicito con el conjunto de tablas criticas cubiertas

No se aprueba introducir una abstraccion nueva ni un parser de migraciones.

## Testing aprobado

Se anadira una suite dedicada en `scripts/tests/` para fijar el contrato del script.

Cobertura minima requerida:

1. normalizacion de `postgresql://` a `postgresql+psycopg://`
2. `OK` cuando el schema desechable contiene las cuatro tablas con sus columnas minimas
3. `FAIL` cuando falta `query_audit_log.response_payload`
4. `FAIL` cuando falta `query_audit_log.entry_id`
5. `FAIL` cuando falta `query_audit_log.created_at`
6. `FAIL` cuando falta `dgt_queue.status`
7. `FAIL` cuando falta la unicidad de `dgt_queue(worker_name, source_entity_id)`
8. `FAIL` cuando falta `documento_interpretativo.row_provenance`
9. `FAIL` cuando falta una tabla completa, no solo una columna

## Riesgos y limites

- este gate puede necesitar ampliacion futura cuando nuevas fases conviertan otras tablas/columnas en dependencias reales del deploy
- el script seguira pudiendo dar verde aunque falten otros indices o constraints no criticos para el runtime actual; el unico endurecimiento adicional aprobado en `5.2` es la unicidad de `dgt_queue(worker_name, source_entity_id)`
- el script tampoco detecta problemas de datos, solo de estructura

## Resultado esperado

Tras `5.2`, un deploy con drift relevante en auditoria MCP, cola DGT o row quality de `documento_interpretativo` debe fallar en `verify_schema.py` antes de declarar el esquema como valido.

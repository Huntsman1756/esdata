# Diseno: MCP Fase 4.1 - Separar cola DGT de `source_revision`

## Objetivo

Separar el estado operativo de cola del worker DGT del estado de revision compartido para que `source_revision` vuelva a significar una sola cosa: la ultima revision real conocida de una entidad fuente.

La fase no intenta rehacer todo el worker DGT. El objetivo exacto es dejar de usar `content_hash_sha256` como almacenamiento dual de hash real y sentinels de cola (`pending`, `empty`, equivalentes historicos).

## Contexto

Hoy `apps/workers/dgt.py` usa `source_revision` como cola persistente:

- seed y discovery insertan filas `pending`
- procesado exitoso reutiliza la misma fila para escribir el hash real
- documentos sin contenido util marcan `empty`

El problema es estructural porque `apps/workers/change_detection.py` interpreta `content_hash_sha256` como un hash real compartido por varios workers. Mientras DGT siga escribiendo sentinels ahi, `source_revision` deja de ser un contrato fiable.

## Decision de diseno

Se introduce una tabla dedicada `dgt_queue`.

`dgt_queue` sera la unica dueña del estado de cola DGT:

- `pending`
- `processed`
- `empty`

`source_revision` queda reservada para revisiones reales de contenido. DGT seguira usando `check_content_changed()` y `record_revision()` para hashes reales, pero ya no escribira estados de cola en esa tabla.

## Alcance aprobado

Archivos obligatorios:

- `apps/workers/dgt.py`
- `apps/workers/tests/test_dgt.py`
- `alembic/versions/20260504_0057_dgt_queue_split.py`
- `apps/api/tests/test_alembic_integrity.py`
- `docs/master-execution-roadmap.md`
- `docs/operations/agent-notes.md`

Archivos documentales de esta fase:

- `docs/superpowers/specs/2026-05-04-mcp-fase-4-1-dgt-queue-design.md`
- `docs/superpowers/plans/2026-05-04-mcp-fase-4-1-dgt-queue-split.md`

## Schema aprobado

Se crea `dgt_queue` con estas columnas:

- `id`
- `worker_name`
- `source_entity_id`
- `dgt_url`
- `status`
- `queued_at`
- `processed_at`

Contrato minimo:

- unique por `(worker_name, source_entity_id)`
- indice de lectura para filas `pending`
- `status` limitado a `pending`, `processed`, `empty`

## Migracion aprobada

La migracion debe:

1. crear `dgt_queue`
2. backfillear desde `source_revision` todas las filas DGT identificables por `source_entity_tipo = 'consulta'` y `dgt_url IS NOT NULL`
3. traducir estado historico asi:
   - `pending` -> `pending`
   - `empty` -> `empty`
   - cualquier hash SHA-256 valido -> `processed`
   - cualquier sentinel legacy no hash (`processed`, `unchanged`, equivalentes) -> `processed`
4. borrar de `source_revision` las filas DGT que no contengan un hash SHA-256 real

La migracion no limpia todavia `dgt_url` ni indices legacy de `source_revision`. Ese cleanup profundo queda fuera de 4.1.

## Runtime aprobado

### Cola DGT

`apps/workers/dgt.py` pasa a tener un helper local para garantizar `dgt_queue` solo en SQLite/tests. En Postgres la tabla pertenece a Alembic y el helper debe degradar a no-op defensivo, igual que `ensure_source_revision_table()`.

Helpers afectados:

- `_ensure_dgt_queue()` inserta en `dgt_queue`
- `_get_pending_urls()` lee `pending` desde `dgt_queue`
- `_mark_done()` actualiza `dgt_queue.status` y `processed_at`

### Discovery

La memoria `existing_ids` de discovery debe salir de `dgt_queue`, no de `source_revision`, porque la cola es quien decide si una referencia ya fue vista.

### Processing

Cuando el documento tenga contenido objetivo:

- `check_content_changed()` consulta solo revisiones reales en `source_revision`
- `record_revision()` escribe el hash real en `source_revision`
- `_mark_done(..., status='processed')` cierra la fila en `dgt_queue`

Cuando no haya resultados o no existan normas objetivo:

- no se escribe sentinel en `source_revision`
- `_mark_done(..., status='empty')` cierra la fila en `dgt_queue`

## Estrategia de tests aprobada

La implementacion se hace con TDD.

Casos minimos a fijar en rojo:

1. seed queue: `_ensure_dgt_queue()` guarda la entrada en `dgt_queue` y deja `source_revision` vacia
2. sync exitoso: `run_sync()` deja `dgt_queue.status = 'processed'` y `source_revision.content_hash_sha256` con hash real
3. sync sin normas objetivo: `run_sync()` deja `dgt_queue.status = 'empty'` y no deja fila sentinel en `source_revision`
4. integridad Alembic: la nueva revision define `dgt_queue`, backfill y borrado de sentinels no hash

## Fuera de alcance

4.1 no debe:

- cambiar el contrato JSON del API
- rehacer la estrategia completa de discovery DGT
- introducir requeue automatico de filas `processed`
- eliminar `dgt_url` de `source_revision`
- limpiar indices legacy no estrictamente necesarios
- tocar otros workers

## Riesgos y decisiones explicitas

- el worker DGT sigue siendo una cola persistente one-shot por referencia; 4.1 corrige la separacion de responsabilidades, no la politica de refresco futuro
- mantener `dgt_url` en `source_revision` es deuda aceptada de este slice porque no rompe el contrato de revision si el hash deja de mezclar estados
- el backfill migra tanto filas `pending` como historico `empty/processed` a `dgt_queue` para no perder trazabilidad operativa

## Criterio de cierre

4.1 se podra cerrar cuando:

- exista la migracion de `dgt_queue`
- DGT deje de escribir sentinels de cola en `source_revision`
- los tests DGT cubran `processed` y `empty`
- haya evidencia fresca de tests/lint del scope afectado
- el roadmap deje el siguiente paso exacto de 4.2 o el siguiente slice MCP decidido

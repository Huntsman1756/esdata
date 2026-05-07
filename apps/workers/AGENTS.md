# AGENTS - apps/workers

## Alcance

Estas reglas aplican a `apps/workers/`.

## Objetivo del modulo

- `apps/workers/` contiene ingestion, normalizacion y enriquecimiento por fuente.
- Cada worker debe ser trazable, idempotente cuando aplique y verificable con tests especificos.

## Estructura esperada

- un modulo por fuente o workflow claro
- `tests/` con fixtures locales y pruebas por worker
- utilidades compartidas solo cuando reduzcan duplicacion real

## Boundary operativo

- `apps/workers/` contiene runtime importable de ingestion y normalizacion
- seeds, backfills, wrappers, verificaciones manuales y scripts de mantenimiento viven en `scripts/`
- si un archivo puede ejecutarse manualmente sin formar parte del runtime del worker, debe salir de `apps/workers/`

## Patrones de concurrencia

### Advisory locks

Los workers BOE y AEAT usan advisory locks de PostgreSQL para evitar ejecuciones concurrentes:

- `boe.py`: `BOE_SYNC_LOCK_KEY = 88420032` — lock a nivel de job con `pg_try_advisory_xact_lock()` en autocommit
- `aeat_models.py`: `AEAT_SYNC_LOCK_KEY = 88420031` — lock a nivel de job con `pg_try_advisory_lock()`
- `change_detection.py`: lock por entidad `pg_advisory_xact_lock(hashtext(lock_key))` para evitar solapamientos `worker-boe` vs `cron-boe-daily`

Si un lock no se adquiere, el worker salta la ejecucion sin error (es un comportamiento esperado).

### Heartbeat loop

Todos los workers persistentes siguen el patron de `runtime.py`:

- `touch_heartbeat()` cada ciclo para marcar actividad
- `sleep_with_heartbeat()` con chunks de 60s para mantener heartbeat durante intervals largos
- `handle_worker_failure()` conecta fallos a Dead-Letter Queue (`sync_dead_letter`)
- Los workers con DLQ llaman `handle_worker_failure(engine, "worker-name", entity_id, entity_type, exc)` en el `except` del loop
- Si `retry_count >= max_retries`, la entidad se mueve a DLQ y se re-lanza la excepcion
- `GracefulShutdownRequested()` se lanza en SIGTERM/SIGINT para break del loop

## Reglas duras

- No meter snapshots, notebooks o debug suelto en esta carpeta.
- Si algo es un script manual de mantenimiento, debe vivir en `scripts/`.
- Mantener separados extractor, parser y normalizacion cuando el modulo crezca.
- Toda integracion externa debe dejar trazabilidad a fuente oficial cuando aplique.

## Verificacion minima

- `pytest apps/workers/tests -v --tb=short`
- `ruff check apps/workers`

## Documentacion relacionada

- `docs/operations/worker-failures.md`
- `docs/operations/runbooks/`

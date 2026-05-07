# AGENTS - scripts

## Alcance

Estas reglas aplican a `scripts/`.

## Objetivo del modulo

- `scripts/` agrupa tooling manual y automatizable que no forma parte del runtime del producto.

## Clasificacion

- `dev/` — utilidades de desarrollo local
- `ops/` — tareas operativas y despliegue
- `data/` — seeds, backfills y transformaciones de datos
- `eval/` — benchmark, evaluacion y quality gates
- `maintenance/` — verificaciones, diagnostico y saneamiento

## Scripts activos

- `scripts/hermes_monitor.py` — Monitor real-time: polling `/status` cada 5min, auto-restart Docker de workers unhealthy, reporte DLQ
- `scripts/ops/worker_scheduler_guard.py` — Guard del scheduler de workers
- `scripts/maintenance/validate-cron-run.py` — Validacion de ejecuciones cron
- `scripts/maintenance/verify_schema.py` — Verificacion de schema despues de migraciones
- `scripts/maintenance/validate-cron-run.py` — Verifica que los cron jobs se ejecutaron correctamente

## Reglas duras

- No crear scripts nuevos dentro de `apps/api` o `apps/workers` si no son runtime real.
- Nombrar scripts por accion concreta.
- Si un script toca DB, infra o datos, documentar precondiciones y modo seguro.
- Mantener outputs, telemetry y resultados en subdirectorios dedicados.

## Verificacion minima

- Ejecutar solo el script afectado con parametros seguros o `--dry-run` si existe.
- Mantener tests en `scripts/tests/` cuando el script tenga logica no trivial.

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

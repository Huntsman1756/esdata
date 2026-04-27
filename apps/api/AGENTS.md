# AGENTS - apps/api

## Alcance

Estas reglas aplican a `apps/api/`.

## Objetivo del modulo

- `apps/api/` contiene el runtime del backend FastAPI, contratos, middleware y superficies MCP/API.
- No debe usarse como cajon para scripts manuales, seeds ad hoc o verificaciones locales.

## Estructura esperada

- `routers/` — endpoints HTTP por dominio
- `services/` — logica de consulta y orquestacion reutilizable
- `middleware/` — autenticacion, seguridad, rate limit, logging y metrics
- `banking/` — utilidades y parsing bancario del dominio
- `tests/` — tests del API
- modulos raiz permitidos solo si son runtime claro: `main.py`, `db.py`, `schemas.py`, `mcp_*`, `agent_monitor.py`, `embeddings.py` y datos de apoyo del API

## Boundary operativo

- seeds, backfills, verificaciones manuales, wrappers de servidor y scripts de exploracion viven en `scripts/`
- `apps/api/` no debe contener utilidades ad hoc ni comandos de uso manual salvo que formen parte del runtime importable

## Reglas duras

- No meter logica de negocio en frontend; el contrato vive aqui.
- Toda mutacion valida input y aplica allowlist explicita.
- No introducir scripts nuevos en la raiz de `apps/api/`; ponerlos en `scripts/`.
- Mantener imports claros y evitar dependencias circulares entre `routers/` y `services/`.
- Si un modulo deja de ser runtime y pasa a ser herramienta manual, moverlo fuera de `apps/api/`.

## Verificacion minima

- `pytest apps/api/tests -v --tb=short`
- `ruff check apps/api`

## Documentacion relacionada

- `docs/master-execution-roadmap.md`
- `docs/manual-usuario/`
- `docs/README.md`

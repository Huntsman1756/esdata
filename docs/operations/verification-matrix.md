# Matriz de verificacion

## Objetivo

Definir que checks minimos ejecutar segun el area tocada del repo y dejar una bateria base reutilizable antes de commit, despliegue o cierre de sesion.

## Bateria minima antes de cualquier commit

```bash
# 1. Contratos HTTP y smoke
pytest apps/api/tests/test_smoke.py \
       apps/api/tests/test_status_contract.py \
       apps/api/tests/test_mcp_contract.py -q

# 2. Nucleo de consulta y grounding
pytest apps/api/tests/test_reranker.py \
       apps/api/tests/test_search_legislacion.py \
       apps/api/tests/test_grounding.py \
       apps/api/tests/test_faithfulness.py -q

# 3. Auditoria y persistencia
pytest apps/api/tests/test_query_audit.py \
       apps/api/tests/test_query_audit_http.py \
       apps/api/tests/test_persistence.py -q

# 4. Integridad de migraciones
pytest apps/api/tests/test_alembic_integrity.py -q

# 5. Lint minimo
ruff check apps/api apps/workers scripts libs --select E,F --quiet
```

## Bateria completa antes de despliegue o cambio grande

```bash
# Todo lo anterior mas:
pytest apps/api/tests/ -q --tb=short
pytest apps/workers/tests/ -q --tb=short
pytest scripts/tests/ -q --tb=short
npm --prefix apps/web run test
npm --prefix apps/web run build
alembic -c alembic.ini heads
```

## Que testear segun que tocas

| Area modificada | Verificacion minima |
|---|---|
| `apps/api/routers/` o `apps/api/services/` | test del area + `apps/api/tests/test_smoke.py` |
| `apps/api/schemas.py` | `apps/api/tests/test_smoke.py` + `apps/api/tests/test_query_audit_http.py` |
| busqueda, reranking o grounding | `test_reranker.py` + `test_search_legislacion.py` + `test_grounding.py` + `test_faithfulness.py` |
| auditoria o persistencia | `test_query_audit.py` + `test_query_audit_http.py` + `test_persistence.py` |
| migraciones Alembic | `test_alembic_integrity.py` + `alembic upgrade head` en DB desechable |
| un worker concreto | `apps/workers/tests/test_<worker>.py` + `ruff check apps/workers` |
| contratos HTTP o `response_model` | `test_smoke.py` + `test_status_contract.py` + `test_mcp_contract.py` + `test_query_audit_http.py` |
| frontend `apps/web` | `npm --prefix apps/web run test` + `npm --prefix apps/web run build` |
| solo docs | comprobacion manual de rutas, enlaces y consistencia con `docs/master-execution-roadmap.md` |

## Cierre de sesion

En shell POSIX:

```bash
pytest apps/api/tests/test_smoke.py \
       apps/api/tests/test_alembic_integrity.py \
       apps/api/tests/test_query_audit.py -q && \
ruff check apps/api --select E,F --quiet && \
alembic -c alembic.ini heads
```

En PowerShell 5.1:

```powershell
pytest apps/api/tests/test_smoke.py apps/api/tests/test_alembic_integrity.py apps/api/tests/test_query_audit.py -q
if ($?) { ruff check apps/api --select E,F --quiet }
if ($?) { alembic -c "alembic.ini" heads }
```

Si estos checks pasan, el repo esta en estado dejable.

Si alguno falla, no cierres la sesion sin dejar el gap documentado en `docs/master-execution-roadmap.md`.

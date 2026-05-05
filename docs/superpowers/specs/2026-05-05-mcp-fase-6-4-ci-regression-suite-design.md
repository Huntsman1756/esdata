# Diseno - Fase 6.4 suite minima de regresion MCP en CI

## Objetivo

Anadir a CI una suite MCP minima y explicita que automatice los contratos MCP mas estables del repo actual, reutilizando tests y gates ya existentes, sin crear nuevas suites ni redisenar la matriz completa de CI.

## Problema confirmado

- `Fase 6.1` ya alineo la documentacion activa entre `REST/OpenAPI`, `HTTP MCP`, `stdio MCP` y `OpenCode -> HTTP MCP`.
- `Fase 6.2` ya introdujo un gate documental local en `scripts/maintenance/verify-doc-contracts.py`.
- `Fase 6.3` ya documento un checklist manual de `GO` / `NO-GO` para release MCP.
- La CI actual en `.github/workflows/ci.yml` todavia no ejecuta ninguna suite MCP minima y explicita; solo corre el barrido general de tests Python y algunos gates adyacentes.
- `docs/reference/mcp-remediation-plan.md` define `6.4` como la fase para llevar una suite de regresion MCP a CI.

## Decision

- `Fase 6.4` se limitara a automatizar una suite MCP minima dentro de `test-python`.
- No se creara un job nuevo de CI.
- No se anadiran tests nuevos en este slice.
- La suite MCP minima reutilizara solo estas piezas existentes:
  - `python scripts/maintenance/verify-doc-contracts.py`
  - `python -m pytest apps/api/tests/test_mcp_private.py -q`
  - `python -m pytest apps/api/tests/test_mcp_contract.py -q`

## Alcance aprobado

Incluye:

- modificar `.github/workflows/ci.yml`
- insertar un bloque MCP minimo y explicito dentro de `test-python`
- actualizar `docs/master-execution-roadmap.md` para reclamar y cerrar `6.4`

No incluye:

- nuevos archivos de test
- nuevos scripts de mantenimiento
- mover tests MCP a un job dedicado
- anadir `test_mcp_transport.py` u otras suites MCP extra
- eliminar la duplicacion con el barrido general `pytest apps/api/tests/ apps/workers/tests/ -v --tb=short`

## Integracion en CI

### Archivo

- `.github/workflows/ci.yml`

### Job objetivo

- `test-python`

### Posicion del nuevo bloque

Despues de `Bootstrap database` y antes de `Run Python tests`.

El objetivo es fallar pronto con una senal MCP explicita, reutilizando el entorno que `test-python` ya prepara (`Postgres`, `DATABASE_URL`, `APP_ENV=test`, dependencias API/workers).

### Pasos a anadir

El bloque MCP minimo debe contener exactamente estas tres comprobaciones como pasos separados y visibles en CI:

1. `python scripts/maintenance/verify-doc-contracts.py`
2. `python -m pytest apps/api/tests/test_mcp_private.py -q`
3. `python -m pytest apps/api/tests/test_mcp_contract.py -q`

### Razon de diseno

- `verify-doc-contracts.py` fija en CI el boundary documental ganado en `6.1` y `6.2`.
- `test_mcp_private.py` fija el contrato MCP privado y su transporte principal.
- `test_mcp_contract.py` fija el contrato MCP publico/esperado a nivel de API/tests existentes.
- Integrarlo en `test-python` evita duplicar setup y mantiene el scope pequeno.

## Limitaciones aceptadas en esta fase

- algunos tests MCP pueden volver a ejecutarse dentro del barrido general de `Run Python tests`
- la suite MCP automatizada sigue siendo minima, no exhaustiva
- `golden questions` nuevas o cobertura MCP mas amplia quedan fuera de este slice

## Roadmap

`docs/master-execution-roadmap.md` debe:

- reclamar `6.4` al empezar la implementacion
- cerrarla tras verificar que `.github/workflows/ci.yml` contiene el bloque MCP minimo
- dejar el estado MCP sin nueva fase reclamada si el plan activo no define una `6.5`

## Verificacion prevista

- lectura de `.github/workflows/ci.yml` para confirmar que `test-python` contiene el bloque MCP minimo
- comprobacion de que los tres comandos referenciados existen hoy en el repo
- lectura del resumen vivo del roadmap para confirmar reclamo y cierre correctos

## Aceptacion

- `.github/workflows/ci.yml` ejecuta explicitamente el gate documental MCP y las dos suites MCP minimas dentro de `test-python`
- no se crean nuevos tests ni scripts en este slice
- el roadmap queda listo para cerrar `6.4`
- la CI ya contiene una senal MCP automatizada, aunque siga siendo minima

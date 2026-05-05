# Plan - Fase 5.4 worker set alignment

## Contexto

- Fase origen: `docs/reference/mcp-remediation-plan.md#54-alinear-worker-set-del-deploy-con-el-scope-real`
- Fuente de verdad del scope runtime: `infra/deploy/docker-compose.prod.yml`
- Flujo canonico afectado: `scripts/ops/deploy-hetzner.sh`

## Task 1 - Fijar regresion roja del worker set canonico

Objetivo:

- Derivar desde `docker-compose.prod.yml` el set de servicios `worker-*` continuos sin `profiles`.
- Verificar que el deploy canonico y los runbooks activos arrancan exactamente ese set.

Archivo principal:

- `scripts/tests/test_deploy_hetzner.py`

Rojo esperado inicial:

- la regresion falla porque el deploy canonico y/o los runbooks siguen omitiendo `worker-cendoj`, `worker-eurlex`, `worker-bde` y `worker-aepd`.

## Task 2 - Alinear deploy canonico y docs activas

Objetivo:

- Actualizar `scripts/ops/deploy-hetzner.sh` para arrancar todos los workers continuos del scope real.
- Actualizar `docs/deployment/server-installation.md` y `docs/operations/runbooks/deploy-compose.md` para documentar el mismo worker set.

Archivos:

- `scripts/ops/deploy-hetzner.sh`
- `docs/deployment/server-installation.md`
- `docs/operations/runbooks/deploy-compose.md`

## Task 3 - Verificar y cerrar fase

Verificacion minima:

- `python -m pytest scripts/tests/test_deploy_hetzner.py -q`
- `bash -n "scripts/ops/deploy-hetzner.sh"`

Cierre:

- actualizar `docs/master-execution-roadmap.md` a `Fase 5.4 [COMPLETA]`
- anadir la nota reusable a `docs/operations/agent-notes.md`

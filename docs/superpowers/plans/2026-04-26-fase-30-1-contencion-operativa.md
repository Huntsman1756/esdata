# Fase 30.1 Contencion Operativa Inmediata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** endurecer `esdata` para que API y `/mcp` fallen cerrados por defecto, el rate limiting actue antes del handler y CI deje de ocultar fallos reales.

**Architecture:** el corte se concentra en los bordes del sistema, no en la logica de negocio. Primero se fijan tests que prueban auth obligatoria, proteccion de `/mcp` y orden correcto del rate limit; despues se aplican cambios minimos en middlewares, arranque y workflows para alinear runtime, CI e infra con un modelo `fail-closed`.

**Tech Stack:** FastAPI, Starlette middleware, pytest, GitHub Actions, Docker Compose.

---

### Task 1: Reclamar fase y fijar spec/plan

**Files:**
- Modify: `docs/master-execution-roadmap.md`
- Create: `docs/superpowers/specs/2026-04-26-fase-30-1-contencion-operativa-design.md`
- Create: `docs/superpowers/plans/2026-04-26-fase-30-1-contencion-operativa.md`

- [ ] Registrar `Fase 30.1` como `EN CURSO` en el resumen vivo
- [ ] Mantener el siguiente paso exacto apuntando a `30.1`
- [ ] Dejar spec y plan cortos alineados con el roadmap

### Task 2: Tests rojos de auth y rate limiting

**Files:**
- Modify: `apps/api/tests/test_security.py`

- [ ] Anadir tests que exijan `401` por defecto en `/v1/*` sin `X-API-Key`
- [ ] Anadir test que compruebe que `/health` sigue siendo publico
- [ ] Anadir test para verificar que el rate limiter corta antes de ejecutar el handler
- [ ] Ejecutar solo esos tests y confirmar fallo por comportamiento actual inseguro

### Task 3: Endurecer auth API y `/mcp`

**Files:**
- Modify: `apps/api/middleware/api_key_auth.py`
- Modify: `apps/api/mcp_security.py`
- Modify: `apps/api/main.py`

- [ ] Eliminar modo fail-open generico en auth API
- [ ] Hacer obligatoria la proteccion de `/mcp` en runtime normal
- [ ] Endurecer validacion de arranque para claves requeridas
- [ ] Ejecutar tests de seguridad hasta verde

### Task 4: Hacer rate limiting pre-handler

**Files:**
- Modify: `apps/api/middleware/rate_limit.py`

- [ ] Reordenar middleware para decidir `429` antes de `call_next`
- [ ] Mantener headers coherentes en respuestas permitidas
- [ ] Ejecutar tests del middleware y de seguridad afectados

### Task 5: Endurecer CI e infra documental

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/deploy-hetzner.yml`
- Modify: `infra/deploy/docker-compose.prod.yml`
- Modify: `docs/environment-variables.md`

- [ ] Quitar `--exit-zero` de `ruff`
- [ ] Corregir la ruta de secrets audit
- [ ] Eliminar o reemplazar pasos que llaman scripts inexistentes
- [ ] Anadir `permissions` minimos explicitos a workflows
- [ ] Reflejar claves obligatorias y defaults seguros en infra y docs

### Task 6: Verificacion y cierre documental

**Files:**
- Modify: `docs/master-execution-roadmap.md`
- Modify: `docs/manual-usuario/04-operacion-tecnica.md` (si aplica)
- Modify: `docs/operations/agent-notes.md` (si aparece alguna trampa tecnica no obvia)

- [ ] Ejecutar tests del scope afectado
- [ ] Comprobar consistencia entre runtime endurecido y docs actualizadas
- [ ] Marcar Fase 30.1 como `COMPLETADA` o `BLOQUEADA` con evidencia real

# Produccion Modelos Green Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corregir el worker productivo de modelos AEAT para que deje de generar errores falsos en `sync_log`, validar el scope afectado y desplegar el fix al VPS.

**Architecture:** El corte se centra en `apps/workers/aeat_models.py` con TDD sobre dos comportamientos: normalizacion de URLs AEAT y filtrado defensivo de recursos oficiales. Despues se valida el scope `workers/api`, se hace commit convencional y se despliega con Docker Compose al VPS.

**Tech Stack:** Python, pytest, ruff, Docker Compose, FastAPI, PostgreSQL.

---

### Task 1: Reproducir el bug con tests

**Files:**
- Modify: `apps/workers/tests/test_aeat_models.py`

- [ ] Escribir test que exija normalizar `url_info` antes de `fetch_detail()`.
- [ ] Escribir test que exija ignorar recursos externos no oficiales al extraer/descargar recursos.
- [ ] Ejecutar solo esos tests y confirmar fallo inicial.

### Task 2: Implementar fix minimo en el worker

**Files:**
- Modify: `apps/workers/aeat_models.py`
- Modify: `apps/workers/tests/test_aeat_models.py`

- [ ] Normalizar `url_info` en `_fetch_model_metadata()`.
- [ ] Introducir helper minimo para validar hosts oficiales de recursos.
- [ ] Filtrar recursos externos en `_extract_model_resources()`.
- [ ] Reforzar `run_sync()` para no descargar recursos fuera de allowlist aunque entren por metadata.
- [ ] Ejecutar tests dirigidos hasta verde.

### Task 3: Verificacion local del scope afectado

**Files:**
- Modify: `docs/master-execution-roadmap.md`

- [ ] Ejecutar `ruff check apps/workers`.
- [ ] Ejecutar `python -m pytest apps/workers/tests/test_aeat_models.py -q --tb=short`.
- [ ] Ejecutar verificaciones minimas de API relacionadas con modelos si siguen estables.
- [ ] Actualizar roadmap con evidencia fresca del slice.

### Task 4: Commit, push y deploy

**Files:**
- Modify: `docs/operations/runbooks/deploy-compose.md` solo si el proceso real requiere ajuste documental

- [ ] Revisar diff y separar solo cambios de este slice.
- [ ] Crear commit convencional.
- [ ] Push de la rama al remoto.
- [ ] Sincronizar snapshot de codigo al VPS.
- [ ] Ejecutar deploy Compose con build y revalidacion remota.

### Task 5: Revalidacion productiva

**Files:**
- No code changes required unless verification fails

- [ ] Ejecutar run productivo de `cron-modelos-daily` o `worker-modelos` segun corresponda.
- [ ] Verificar `sync_log` reciente para `worker-modelos` y `cron-modelos-daily`.
- [ ] Verificar `Alertmanager`, `health`, `status`, `modelo 303` y estado Compose.
- [ ] Documentar resultado final con evidencia y riesgos residuales.

# Fase 30.2 Persistencia Durable Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** sustituir stores en memoria de gobernanza AI por persistencia durable y anadir un query audit log versionado y consultable.

**Architecture:** la persistencia se resuelve con tablas relacionales y JSON donde aporta flexibilidad, manteniendo contratos de servicio y routers lo mas estables posible. Se prioriza que `ai_audit`, `data_lineage`, `human_review`, `model_registry`, `ai_config_version` y `query_audit_log` sobrevivan reinicios y puedan consultarse via servicios/routers existentes con el menor churn posible.

**Tech Stack:** FastAPI, SQLAlchemy Core/ORM ligero, Alembic, SQLite para tests, PostgreSQL para runtime.

---

### Task 1: Migracion y schema de persistencia AI

**Files:**
- Create: `alembic/versions/20260426_0030_ai_governance_persistence.py`

- [ ] Crear tablas para `ai_audit_log`, `data_lineage`, `human_review`, `ai_model_registry`, `ai_config_version` y `query_audit_log`
- [ ] Anadir indices minimos por `request_id`, `created_at`, `status`, `tabla`, `model_id`, `activo`

### Task 2: TDD servicios persistentes

**Files:**
- Modify: `apps/api/services/ai_audit.py`
- Modify: `apps/api/services/data_lineage.py`
- Modify: `apps/api/services/human_review.py`
- Modify: `apps/api/services/model_registry.py`
- Create: `apps/api/services/query_audit.py`
- Test: `apps/api/tests/test_ai_audit_log.py`
- Test: `apps/api/tests/test_data_lineage.py`
- Test: `apps/api/tests/test_human_review.py`
- Test: `apps/api/tests/test_model_registry.py`
- Test: `apps/api/tests/test_query_audit.py`

- [ ] Escribir/ajustar tests para persistencia real y supervivencia entre lecturas del servicio
- [ ] Implementar acceso DB sin stores en memoria como fuente primaria

### Task 3: Integracion con middleware y routers

**Files:**
- Modify: `apps/api/middleware/ai_audit.py`
- Modify: `apps/api/routers/ai_audit_log.py`
- Modify: `apps/api/routers/human_review.py`
- Modify: `apps/api/routers/data_lineage.py`
- Modify: `apps/api/routers/model_registry.py`

- [ ] Hacer que middleware/router lean y escriban sobre persistencia durable
- [ ] Mantener contratos HTTP existentes donde sea razonable

### Task 4: Verificacion y cierre documental

**Files:**
- Modify: `docs/master-execution-roadmap.md`
- Modify: `docs/manual-usuario/04-operacion-tecnica.md` si cambia operacion visible
- Modify: `docs/operations/agent-notes.md` si aparece una trampa tecnica relevante

- [ ] Ejecutar tests del scope AI governance
- [ ] Cerrar `30.2` con evidencia real o marcarlo bloqueado si aparece un impedimento estructural

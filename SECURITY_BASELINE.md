# Security Baseline — ESData

> **Estado:** Inventario de controles de seguridad S-TIER.
> **Fuente de reglas:** `AGENTS.md` (18 reglas no negociables).
> **Compliance docs:** `docs/COMPLIANCE.md` (auditorías externas).
> **Última auditoría:** 2026-04-29 (Fase 42 — Mass Assignment + NEXT_PUBLIC)

---

## Resumen

| Estado | Count |
|--------|-------|
| ✅ IMPLEMENTED | 15 |
| ⚠️ PARCIAL | 2 |
| ❌ TARGET | 1 |

---

## Inventario de Controles

### 1. Backend-only ✅ IMPLEMENTED
- **Regla:** Nunca lógica de negocio ni acceso DB en frontend.
- **Evidencia:** `apps/web/` solo llama al backend via `ESDATA_API_BASE_URL`. No hay acceso DB directo desde cliente.
- **Archivos:** `apps/web/lib/api.ts`, `apps/web/app/api/consulta/route.ts`

### 2. RLS Zero Policy ✅ IMPLEMENTED
- **Regla:** RLS obligatorio en todas las tablas. Sin policies para `public`/`anon`.
- **Evidencia:** Migración `alembic/versions/20260429_0001_rls_zero_policy.py` aplica RLS a 154 tablas, policies solo para `service_role` y `esdata`.
- **Archivos:** `alembic/versions/20260429_0001_rls_zero_policy.py`

### 3. Mass Assignment ✅ IMPLEMENTED
- **Regla:** Validar esquema antes de escribir (allowlist). Prohibido `req.body` directo.
- **Estado:** Todos los endpoints CREATE/UPDATE usan schemas Pydantic con allowlist explícita de campos. `mica.py:update_casp` usa `CASPUpdate` (6 campos allowlist). `crd_brrd_emir.py:update_crd_capital_position` usa `CrdCapitalPositionUpdate` (9 campos allowlist). CREATE endpoints validan con schemas `CASPCreate`, `CrdCapitalPositionCreate`, `CrdStressTestCreate`, `BrrdBailInCreate`, `EmirTradeReportCreate`, `EmirClearingMemberCreate`.
- **Archivos:** `apps/api/schemas.py` (37+ schemas Pydantic), `apps/api/routers/mica.py`, `apps/api/routers/crd_brrd_emir.py`

### 4. Storage ❌ TARGET
- **Regla:** Buckets privados, nombres UUID, acceso via signed URL temporal.
- **Estado:** No existe infraestructura de almacenamiento. Uploads en `banking.py` son stateless (parsed, no persisted).
- **Archivos:** `apps/api/routers/banking.py:72-117`

### 5. Pagos/Webhooks ✅ IMPLEMENTED
- **Regla:** Verificación criptográfica de firma + idempotencia por `event.id`.
- **Estado:** `apps/api/services/webhook_verification.py` — HMAC-SHA256 + idempotencia por `event_id` con tabla `webhook_events` auto-creada.
- **Archivos:** `apps/api/services/webhook_verification.py`, `apps/api/routers/webhooks.py`

### 6. Env vars ✅ IMPLEMENTED
- **Regla:** Nunca secretos hardcodeados ni `NEXT_PUBLIC_*`. Validación de schema al arranque.
- **Estado:** `.env.example` sin secretos. `main.py` valida env vars al arranque. `NEXT_PUBLIC_API_BASE_URL` eliminado de Dockerfile, `.env.example` y frontend. Proxy server-side (`/api/cambios`, `/api/workflow`, `/api/consulta`) usa `ESDATA_API_BASE_URL` (variable de servidor) para reenviar requests al backend.
- **Archivos:** `apps/web/Dockerfile`, `apps/web/.env.example`, `apps/web/app/api/cambios/route.ts`, `apps/web/app/api/workflow/route.ts`, `apps/web/app/api/consulta/route.ts`

### 7. RPC Lockdown ✅ IMPLEMENTED
- **Regla:** Revocar execute a `public`/`anon` tras `CREATE FUNCTION`.
- **Estado:** `alembic/versions/20260429_0002_revoke_function_execute.py` — migración que revoca EXECUTE de PUBLIC en funciones definidas por el usuario (excluye pg_catalog, information_schema, pg_toast). service_role y esdata mantienen EXECUTE explicito. Downgrade reversible.
- **Archivos:** `alembic/versions/20260429_0002_revoke_function_execute.py`

### 8. Input validation + Rate Limiting ✅ IMPLEMENTED
- **Regla:** Validación en toda mutación. Rate limiting en auth, mutaciones, webhooks, uploads, AI.
- **Evidencia:**
  - `middleware/rate_limit.py` — token bucket in-memory, per-endpoint (health:100, v1:60, mcp:30)
  - `middleware/api_key_auth.py` — valida `ESDATA_API_KEY`, bypass `PUBLIC_PATHS`
  - `middleware/ai_safety.py` — detección de inyección por patrones, umbral 0.5
  - `middleware/security_headers.py` — X-Content-Type-Options, X-Frame-Options, HSTS, X-Request-ID
  - `services/file_validation.py` — FileValidator con allowlist extension/MIME, límites, cuarentena
- **Nota:** Rate limiting in-memory (se resetea en restart). No requiere Redis para single-node production.
- **Archivos:** `apps/api/middleware/rate_limit.py`, `apps/api/middleware/api_key_auth.py`, `apps/api/middleware/ai_safety.py`, `apps/api/middleware/security_headers.py`, `apps/api/services/file_validation.py`

### 9. Docker ✅ IMPLEMENTED
- **Regla:** Non-root, sin secretos en capas, imagen base fijada (no `latest`).
- **Evidencia:** Todos los Dockerfiles usan `USER app` (non-root). Sin secretos en capas. Tags con SHA-256 fijos: `python:3.12-slim@sha256:46cb7cc...`, `node:22-slim@sha256:d415caa...`, `caddy:2-alpine@sha256:834468128...`, `pgvector/pgvector:pg16@sha256:7d400e340...`, `redis:7-alpine@sha256:7aec734b2...`.
- **Gap:** `docker-compose.yml` (dev) tiene passwords hardcodeados — aceptable para dev.
- **Archivos:** `apps/api/Dockerfile`, `apps/workers/Dockerfile`, `apps/web/Dockerfile`, `infra/deploy/docker-compose.prod.yml`

### 10. AI Data Leakage ✅ IMPLEMENTED
- **Regla:** Minimizar datos, proteger contra prompt injection, usar endpoints con política de no entrenamiento.
- **Evidencia:**
  - `middleware/ai_audit.py` — log de decisiones AI con request_id, sin prompts/datos personales
  - `services/grounding.py` — `GROUNDING_THRESHOLD=0.4`, detección de inyección en chunks
  - `services/adversarial.py` — detección por patrones (14+ tipos), sin dependencia LLM
  - `services/ai_audit.py` — SQL audit log storage durable
- **Archivos:** `apps/api/middleware/ai_audit.py`, `apps/api/services/grounding.py`, `apps/api/services/adversarial.py`, `apps/api/services/ai_audit.py`

### 11. GitHub/CI ✅ IMPLEMENTED
- **Regla:** Evitar `pull_request_target` con código no confiable, `permissions` mínimos, preferir OIDC.
- **Evidencia:** `ci.yml` con `push` + `pull_request` triggers, `permissions: contents: read`. `deploy-hetzner.yml` con `workflow_dispatch` solo. Sin `pull_request_target`.
- **Gap:** `deploy.yml` (deprecated) usa `${{ secrets.* }}` en vez de OIDC.
- **Archivos:** `.github/workflows/ci.yml`, `.github/workflows/deploy-hetzner.yml`

### 12. Secrets ✅ IMPLEMENTED
- **Regla:** Prohibido `.env` anidados ni commiteados. Solo `.env.example` en repo. Secretos reales fuera.
- **Evidencia:** No hay archivos `.env` commiteados. Solo `.env.example` en repo.
- **Archivos:** `.env.example` (raíz y por módulo)

### 13. Auditoría E2E ✅ IMPLEMENTED
- **Regla:** Todo endpoint de retrieval/consulta/MCP debe tener auditoria E2E.
- **Evidencia:**
  - `services/query_audit.py` — `QueryAuditEntry` con `request_id`, `user_id`, `path`, `query_text`, `retrieved_chunks`, `model_version`, `config_version`, `grounding_status`
  - `services/ai_audit.py` — `AIAuditLogStore` con almacenamiento SQL durable
  - `mcp_security.py` — validación API key MCP + rate limiting por key
  - `mcp_server.py` — FastApiMCP montado en `/mcp`
  - `mcp_stdio.py` — `_log_mcp_call()` integrado en `_handle_tools_call` con try/finally
  - Fallback silencioso: fallos de escritura no rompen operación MCP
- **Archivos:** `apps/api/services/query_audit.py`, `apps/api/services/ai_audit.py`, `apps/api/mcp_security.py`, `apps/api/mcp_server.py`, `apps/api/mcp_stdio.py`

### 14. Parsing de Ficheros ✅ IMPLEMENTED
- **Regla:** Allowlist de tipo, validación MIME, límites de tamaño, cuarentena.
- **Estado:** `services/file_validation.py` — `FileValidator` con allowlist de extensiones/MIME, límites de tamaño, cuarentena manual, validación magic bytes por contenido (XML/JSON/CSV). Integrado en `routers/banking.py` para `iso20022_parse` y `n43_parse`.
- **Archivos:** `apps/api/services/file_validation.py`, `apps/api/routers/banking.py`

### 15. Grounding Duro ⚠️ PARCIAL
- **Regla:** Respuestas factuales con citas exactas por claim. Chunks recuperados = input no confiable.
- **Implementado:** `services/grounding.py` con `validate_claim_grounding()` y `GROUNDING_THRESHOLD=0.4`.
- **Gap:** Sin evidencia de enforcement de citation-per-claim en router code. Threshold configurado pero no validado consistentemente en tiempo de respuesta.
- **Archivos:** `apps/api/services/grounding.py`, `apps/api/schemas.py:379-401`

### 16. Veracidad Documental ✅ IMPLEMENTED
- **Regla:** Usar `[IMPLEMENTED]`/`[PARTIAL]`/`[TARGET]`. No vender roadmap como implementado.
- **Evidencia:** Roadmap y docs usan marcadores correctamente. No se presenta roadmap como implementado.
- **Archivos:** `docs/master-execution-roadmap.md`

### 17. Corpus Autoritativo ⚠️ PARCIAL
- **Regla:** Ningún texto LLM como fuente de verdad.
- **Implementado:** `vocabulary.py` como single source of truth para valores permitidos. `backfill_chunks.py` backfill desde corpus `doctrina`/`legislacion`.
- **Gap:** Sin enforcement técnico de que texto generado por LLM nunca se escribe en DB como autoritativo. La pipeline depende de disciplina de proceso.
- **Archivos:** `apps/api/vocabulary.py`, `scripts/backfill_chunks.py`

### 18. Migraciones ✅ IMPLEMENTED
- **Regla:** Prohibido `CREATE TABLE IF NOT EXISTS` en runtime como sustituto de Alembic.
- **Estado:** Patch en `alembic/env.py:35-58` eliminado. Las 8 migraciones con `CREATE TABLE IF NOT EXISTS` literal convertidas a `CREATE TABLE`. Los 8 archivos `infra/sql/` con IF NOT EXISTS convertidos a CREATE TABLE.
- **Excepción permitida:** `alembic_version` (tabla de tracking de Alembic) mantiene `CREATE TABLE IF NOT EXISTS` en `env.py:122` — necesario para que Alembic funcione.
- **Archivos actualizados:** `alembic/env.py`, `alembic/versions/` (8 archivos), `infra/sql/` (8 archivos)

---

## Compliance Check

Si alguna respuesta es "si" → detener y refactorizar:

- [ ] Frontend habla directo con DB? → NO ✅
- [ ] Escribiendo en DB input sin schema? → NO ✅
- [ ] Creando policy publica/anon? → NO ✅
- [ ] Exponiendo secretos en cliente? → NO ✅
- [ ] Procesando webhooks sin firma? → NO (webhooks verificados) ✅
- [ ] Añadiendo retrieval/MCP sin auditoria? → NO ✅
- [ ] Aceptando parsing remoto inseguro? → NO (FileValidator integrado) ✅
- [ ] Documentando target-state como implementado? → NO ✅

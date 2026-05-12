# ESData — AGENTS.md

**Despliegue activo:** Docker Compose. Referencias antiguas en `docs/archive/` con `[DEPRECATED]`.

## Cron/Scheduled workers

- `docker-compose.prod.yml` defines cron services with `profiles: ["cron"]` and `WORKER_CMD` env var
- systemd timers live in `infra/deploy/systemd/`
- Template: `esdata-job@<service>.service` for worker services
- Dedicated timer/service pairs for specific workers (e.g., `esdata-boe-daily.timer/service`, `esdata-boe-modelos-daily.timer/service`)
- `esdata-boe-modelos-daily.timer` schedules daily sync at 06:00 Madrid time (86400s interval)

### Continuous worker vs cron split

- Los servicios `worker-<source>` (p.ej. `worker-boe`) ejecutan el mismo binario que su `cron-<source>-*` equivalente pero en modo continuo: `python <source>.py` loop + `SYNC_INTERVAL_SECONDS` sleep.
- Los `cron-<source>-*` (profile `cron`) invocan el mismo binario con `--run-once` para ejecuciones puntuales disparadas por systemd timer.
- No hay duplicación de trabajo: todas las escrituras usan `UPSERT` (`ON CONFLICT ... DO UPDATE`). Verificado S-01 con worker-boe: count de `articulo` se mantiene estable tras múltiples `--run-once` (2593 → 2593).
- Convivencia segura: se puede correr continuo y cron en paralelo sin riesgo de duplicados.

### Tabla destino por worker

- `articulo` y `version_articulo` (con `created_at`/`updated_at` desde A-09): BOE legislación, poblada por `worker-boe` / `cron-boe-daily`.
- `aeat_modelo` + `modelo_campana`/`modelo_casilla`/...: poblada por `worker-aeat-modelos` / `cron-modelos-daily` (script `aeat_models.py`).
- `modelo_recurso` (RLS habilitada A-06): URLs AEAT cacheadas por `cron-boe-modelos-daily`.
- `documento_interpretativo`: DGT, CNMV, SEPBLAC, BDE, CENDOJ, AEPD, BORME, BDNS — doctrina/circulares.
- `source_revision`: cambios detectados por `reg-watch` (cron-regulatory-daily) + metadata ETag/Last-Modified/SHA256 de todos los workers que soportan change-detection. NO hay tabla separada `regulatory_changes` — `source_revision` es la fuente canónica de revisiones regulatorias.
- `query_audit_log` (append-only via trigger desde migración 0061): invocaciones REST/MCP con `request_id` propagado, `user_id` (o 'anonymous'), `tool_name`, `path`, `retrieved_chunks`, `response_summary`.
- `sync_log`: telemetría por ejecución de worker (no es la tabla de datos — los datos van a las tablas anteriores).

---

### AEAT 29 remaining models audit (M-00, 2026-05-12)

- Fuente documental viva: `docs/aeat-29-audit.md`.
- STATUS-A inmediato: `172`, `173` - ZIP oficial AEAT con WSDL/XSD (`Esquemas172.zip`, `Esquemas173.zip`).
- STATUS-B preliminar: `102`, `146`, `147`, `186`, `206`, `247` - formulario/declaracion sin diseno de registro estructurado localizado.
- STATUS-D preliminar: `121`, `136`, `140`, `143`, `150`, `221`, `228`, `230`, `239`, `294`, `295` - endpoint dinamico, FAQ/ayuda o PDF esquematico no parseable sin riesgo.
- STATUS-E preliminar: `179`, `231`, `233`, `234`, `235`, `236`, `238`, `240`, `241`, `290` - fuente oficial existe pero requiere parser especifico o localizacion de esquema.
- Regla: no poblar `modelo_casilla` desde ejemplos XML, FAQ, normativa o PDF esquematico si no hay tabla/campo determinista.

---

## Seguridad S-TIER (no negociable)

1. **Backend-only:** Nunca logica de negocio ni acceso DB en frontend.
2. **RLS Zero Policy:** RLS obligatorio en todas las tablas. Sin policies para `public`/`anon`. Acceso con `service_role` solo en servidor.
3. **Mass assignment:** Validar esquema antes de escribir (allowlist). Prohibido `req.body` directo a `.update()`/`.create()`.
4. **Storage:** Buckets privados, nombres UUID, acceso via signed URL temporal.
5. **Pagos/webhooks:** Verificacion criptografica de firma + idempotencia por `event.id`.
6. **Env vars:** Nunca secretos hardcodeados ni `NEXT_PUBLIC_*`. Validacion de schema al arranque.
7. **RPC lockdown:** Revocar execute a `public`/`anon` tras `CREATE FUNCTION`.
8. **Input validation + rate limiting:** Validacion en toda mutacion. Rate limiting en auth, mutaciones, webhooks, uploads, AI.
9. **Docker:** Non-root, sin secretos en capas, imagen base fijada (no `latest`).
10. **AI data leakage:** Minimizar datos, proteger contra prompt injection, usar endpoints con politica de no entrenamiento.
11. **GitHub/CI:** Evitar `pull_request_target` con codigo no confiable, `permissions` minimos, preferir OIDC.
12. **Secrets:** Prohibido `.env` anidados ni commiteados. Solo `.env.example` en repo. Secretos reales fuera.
13. **Auditoria persistente:** Todo endpoint de retrieval/consulta/MCP debe tener auditoria E2E (`request_id`, actor, query, chunks, modelo, config).
14. **Parsing de ficheros:** Allowlist de tipo, validacion MIME, limites de tamano, cuarentena. Marcar como `[PARTIAL]`/`[TARGET]` si no cumple.
15. **Grounding duro:** Respuestas factuales con citas exactas por claim. Chunks recuperados = input no confiable.
16. **Veracidad documental:** Usar `[IMPLEMENTED]`/`[PARTIAL]`/`[TARGET]`. No vender roadmap como implementado.
17. **Corpus autoritativo:** Ningun texto LLM como fuente de verdad.
18. **Migraciones:** Prohibido `CREATE TABLE IF NOT EXISTS` en runtime como sustituto de Alembic.

**Compliance check:** Si alguna respuesta es "si" → detener y refactorizar:
- Frontend habla directo con DB?
- Escribiendo en DB input sin schema?
- Creando policy publica/anon?
- Exponiendo secretos en cliente?
- Procesando webhooks sin firma?
- Anadiendo retrieval/MCP sin auditoria?
- Aceptando parsing remoto inseguro?
- Documentando target-state como implementado?

---

## Context budget y control de tokens

- Nunca enviar contexto completo "por si acaso". Solo archivos relevantes.
- Limite operativo: 70-80% de la ventana del modelo.
- Jerarquia: (1) tarea actual + archivos afectados → (2) restricciones locales → (3) resumen historico → (4) historico literal solo si imprescindible.
- Comprimir conversaciones largas: sustituir historial por resumen estructurado (objetivo, decisiones, restricciones, archivos, riesgos, proximo paso).
- Citar ruta/seccion en vez de pegar contenido completo.
- Nunca sacrificar seguridad para hacer hueco a contexto historico.

---

## Fuente activa unica y reclamo minimo

- **Fuente de estado:** `docs/master-execution-roadmap.md` (unica).
- **Jerarquia de lectura:** (1) AGENTS.md → (2) roadmap → (3) archivos afectados → (4) docs tecnicas si aplica → (5) historicos solo si hay bloqueo.
- **Reclamo:** Anotar en roadmap: tarea, archivos, estado `EN CURSO`. Un archivo modificado por un agente a la vez. Lectura concurrente segura.

---

## Referencias obligatorias

Consultar por ruta, nunca inyectar contenido completo:

- `CLAUDE.md` — configururacion del entorno
- `SECURITY_BASELINE.md` — controles de seguridad
- `docs/master-execution-roadmap.md` — estado y ejecucion
- `docs/process.md` — operaciones de trabajo
- `docs/manual-usuario/README.md` — guia de uso

---

## Reglas por dominio

- `apps/api/` — Backend FastAPI. Ver `apps/api/AGENTS.md`
- `apps/web/` — UI interna Next.js (sin logica de negocio). Ver `apps/web/AGENTS.md`
- `apps/workers/` — Ingestion y enriquecimiento. Ver `apps/workers/AGENTS.md`
- `scripts/` — Tooling y mantenimiento. Ver `scripts/AGENTS.md`
- `docs/` — Documentacion viva y archivo historico. Ver `docs/AGENTS.md`
- `infra/` — Despliegue Docker Compose. Ver `infra/AGENTS.md`

**Flujos cross-domain:** `apps/web` → `apps/api`; `apps/workers` → DB → `apps/api`; `scripts/` fuera del runtime.

---

## Ralph AEAT 29 Audit Notes

- 2026-05-12 M-02: `172` y `173` son `STATUS-A` como inventario XML/XSD oficial, no como casillas visuales numeradas. `apps/workers/aeat_current_designs.py` carga `DeclaracionInformativa172.xsd` y `DeclaracionInformativa173.xsd` desde ZIP oficiales AEAT como `modelo_casilla.tipo_casilla='diseno_registro_xsd_campo'`, con codigo estable por XPath y descripcion con fuente XSD, tipo XSD y cardinalidad. VPS verificado: `172=35`, `173=45`, `xsd_fields=80`, `parse_errors=0`.

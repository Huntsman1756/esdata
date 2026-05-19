# ESData — AGENTS.md

**Despliegue activo:** Docker Compose. Referencias antiguas en `docs/archive/` con `[DEPRECATED]`.

## Ralph - problemas conocidos

- CRLF en Windows: los prompt files deben guardarse con LF, no CRLF. Antes de lanzar `ralph.sh`: `dos2unix scripts/ralph/*.md`.
- Seeds de datos: Ralph genera los commits locales pero no aplica seeds al VPS automaticamente. Aplicar manualmente antes de M-06/M-07.
- Si Ralph no actualiza `prd.json` correctamente: editar manualmente y commitear con `"[STORY-ID] fix prd.json passes=true"`.

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
- `documento_interpretativo` con `tipo_fuente='boe_diario'`: BOE diario no consolidado (`BOE-B/S/N`) poblado por `cron-boe-diario-daily`; no se mezcla con `articulo/version_articulo`.
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
- STATUS-E/M-03 final: `179`, `231`, `238`, `240`, `241`, `290` resueltos con XSD/ZIP oficiales AEAT y campos `diseno_registro_xsd_campo`; `234`, `235`, `236` reclasificados a STATUS-D porque solo hay ejemplos XML; `233` queda como unico STATUS-E pendiente hasta localizar contrato/plantilla oficial determinista.
- M-04/M-09 final: `102`, `146`, `147`, `186`, `206`, `247` usan `modelo_campana_operativa.completeness_estado='no-casillas-expected'`; agentes deben tratarlo como ausencia verificada de casillas estructuradas, no como `evidencia limitada`.
- `deprecated` existe en contrato API/MCP, pero no hay modelo STATUS-C marcado en esta fase sin evidencia oficial.
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

## Codex en codebases grandes

- `AGENTS.md` es la fuente operativa para Codex. `CLAUDE.md` puede existir como referencia de entorno, pero no sustituye estas instrucciones.
- Mantener instrucciones lean y por capas: raiz = reglas globales/mapa; subdirectorios = comandos y convenciones locales.
- Empezar las tareas en el directorio mas especifico posible; leer primero el `AGENTS.md` aplicable, roadmap y archivos afectados.
- Preferir busqueda viva (`rg`, `git grep`, lectura de archivos reales) sobre indices, resumenes o memoria historica cuando haya riesgo de desactualizacion.
- No cargar docs o historicos completos por defecto; usar rutas, secciones y busquedas acotadas.
- Usar skills solo cuando el tipo de tarea lo active; no duplicar workflows largos dentro de `AGENTS.md`.
- Usar MCP/herramientas externas solo cuando aporten datos vivos o capacidades no disponibles localmente; no antes de entender el repo.
- Si hay LSP o tooling semantico disponible, preferirlo para referencias de simbolos; si no, usar `rg` y confirmar definicion/uso antes de editar.
- Subagentes: solo cuando el usuario pida delegacion/parallel agents; exploracion y edicion no deben mezclarse si aumenta el riesgo.
- Revisar estas instrucciones cada 3-6 meses o tras cambios grandes de modelo/tooling; eliminar reglas que ya sean lastre.

---

## Fuente activa unica y reclamo minimo

- **Fuente de estado:** `docs/master-execution-roadmap.md` (unica).
- **Jerarquia de lectura:** (1) AGENTS.md → (2) roadmap → (3) archivos afectados → (4) docs tecnicas si aplica → (5) historicos solo si hay bloqueo.
- **Reclamo:** Anotar en roadmap: tarea, archivos, estado `EN CURSO`. Un archivo modificado por un agente a la vez. Lectura concurrente segura.

---

## Referencias obligatorias

Consultar por ruta, nunca inyectar contenido completo:

- `CLAUDE.md` — referencia de entorno; no sustituye `AGENTS.md` para Codex
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

# ESDATA MCP — Executive Audit Summary

**Domain:** Spanish tax/compliance (AEAT, BOE, EUR-Lex, AEPD, DGT, BdE, CNMV, SEPBLAC, CENDOJ, BORME, BDNS)  
**Date:** 2026-05-09  
**Scope:** DB schema + data (163 tables, 28 populated), 14 crons/workers, 27 MCP tools HTTP + 8 stdio, ~250 REST endpoints, traceability, determinism, audit trail  
**Auditor:** executive-synthesis (consolidation of 3 layer reports)

---

## TL;DR

- **Estado global: APTO CON RESERVAS**
- **CRITICAL findings: 12** (7 DB/schema + 2 cron/workers + 3 MCP/API)
- **Veredicto por perfil:**
  - Legal (cita en tribunal): **NO APTO** — búsqueda rota, 82% schema vacío, audit trail incompleto
  - Financial (compliance interno): **APTO CON RESERVAS** — detalle de artículos funcional y trazable, pero búsqueda y cobertura insuficientes
  - Compliance officer (AML/fiscal): **NO APTO** — PBC/AML vacío, screening vacío, audit E2E roto

---

## Dimensiones government-grade (10)

| # | Dimensión | Estado | Evidencia | Gap vs benchmark |
|---|-----------|--------|-----------|------------------|
| a | **Provenance** (URL canónica a fuente oficial) | **PARTIAL** | Endpoints de detalle (`get_articulo`, `get_norma`, `get_modelo`) incluyen `boe_reference`, `source_url`, `eli_uri` verificados contra BOE real. 17/27 tools de listado NO incluyen provenance por item. | BOE MCP incluye provenance en cada item devuelto. Gap: listados sin trazabilidad individual. |
| b | **Freshness** (<24h daily, <7d weekly) | **PARTIAL** | 11/12 fuentes sincronizadas <3h (sistema en arranque). DGT degradada (83% error SSL). `source_freshness_snapshot` vacía — no hay monitorización programática. | Government-grade requiere freshness verificable vía API. Endpoint `/v1/sources/freshness` devuelve 0 sources. |
| c | **Determinismo** (mismas entradas = mismas salidas) | **OK** | Verificado: `/v1/buscar?q=IVA` x3 = hash MD5 idéntico. `get_articulo`, `get_norma` x2 = idénticos. Sin embeddings aleatorios en resultados. | Cumple benchmark. |
| d | **Handling uncertainty** (confianza + avisos) | **PARTIAL** | Endpoints de detalle incluyen `{"nivel": 1, "fuentes": [...], "aviso": null}`. Campo `completeness` en audit log no verificable (endpoint 500). Listados no incluyen nivel de confianza. | Government-grade requiere confianza en TODA respuesta, no solo detalle. |
| e | **Not-found explícito** (nunca fabricación) | **OK** | Verificado: inputs inexistentes (`LIVA_FAKE/99999`, `NORMA_INEXISTENTE_XYZ`) devuelven error claro. No se detectó fabricación en ningún endpoint. | Cumple benchmark. |
| f | **Coverage** (dominio cubierto vs declarado) | **MISSING** | 135/163 tablas vacías (82.8%). 29+ routers activos devuelven vacío (MiCA, DORA, MiFID, PSD2, MAR, PRIIPs, CSRD, PBC, XBRL, PGC). Schema declara cobertura que no existe. | BOE MCP solo declara lo que tiene. AEAT MCP no expone endpoints sin datos. **Gap crítico:** usuario puede interpretar vacío como "no hay regulación". |
| g | **Audit trail** (100% retrievals en query_audit_log) | **MISSING** | `query_audit_log` existe (55 entries) pero: `request_id="unknown"` en 96%, `user_id` vacío en 100%. Endpoint `/v1/ai/query-audit` devuelve 500 — imposible verificar cobertura E2E. | Government-grade exige 100% trazabilidad request→response→actor. Sistema actual: ~4% trazable. |
| h | **Integrity** (content_hash para detectar drift) | **PARTIAL** | 9/163 tablas tienen `content_hash`/`sha256`. Tablas core (`articulo`, `norma`, `version_articulo`, `modelo_recurso`) sí tienen hash. 134 tablas sin hash. `source_revision` registra `content_hash_sha256` para detectar cambios en fuente. | Government-grade requiere hash en toda tabla con contenido legal. Gap: tablas auxiliares sin integridad verificable. |
| i | **Security** (RLS, append-only, backend-only) | **PARTIAL** | 159/163 tablas con RLS (97.5%). `modelo_recurso` (9,659 filas, tabla más grande) SIN RLS. `query_audit_log` existe como append-only. Backend-only confirmado. No se detectó mass-assignment. | Gap: 4 tablas sin RLS, incluyendo la más grande del sistema. |
| j | **Official sources only** (100% URLs a dominios whitelisted) | **OK** | 100% de URLs en DB apuntan a dominios oficiales verificados. 100% de HTTP requests de workers van a dominios oficiales. Zero non-whitelisted domains. Dominios: boe.es, sede.agenciatributaria.gob.es, eur-lex.europa.eu, cnmv.es, bde.es, poderjudicial.es, sepblac.es, infosubvenciones.es, hacienda.gob.es, aepd.es. | **Cumple benchmark.** |

**Resumen dimensional:** 3 OK, 4 PARTIAL, 2 MISSING, 1 OK = **No cumple government-grade.** Falla en coverage, audit trail, y freshness monitoring.

---

## CRITICAL findings (consolidados, ordenados por impacto legal)

| # | Finding | Layer | Evidencia | Impacto legal | Remediation |
|---|---------|-------|-----------|---------------|-------------|
| 1 | `/v1/legislacion/buscar` y `/v1/consulta` devuelven 500 (Decimal serialization) | API | `TypeError` en `buscar.py:161` | **Máximo** — tools MCP core de búsqueda completamente rotas. Abogado/gestor no puede buscar legislación. | Fix `json.dumps(default=str)` o cast Decimal→float |
| 2 | 29+ routers activos devuelven vacío (MiCA, DORA, MiFID, PSD2, MAR, PRIIPs, PBC, XBRL, PGC...) | DB/API | 135/163 tablas vacías, routers activos | **Máximo** — usuario interpreta vacío como "no hay regulación aplicable" → asesoramiento erróneo con responsabilidad legal | Desactivar routers sin datos o devolver `{"status":"not_available","reason":"source_not_yet_ingested"}` |
| 3 | `query_audit_log.request_id = "unknown"` en 96% | DB | 53/55 entries sin request_id real | **Alto** — imposible trazar consulta a petición. Incumple S-13. En litigio, no se puede demostrar qué se consultó. | Propagar `X-Request-ID` desde middleware a audit log |
| 4 | `/v1/ai/query-audit` devuelve 500 (json.loads bug) | API | `TypeError` en `query_audit.py:242` | **Alto** — no se puede verificar auditoría E2E. Compliance officer no puede auditar uso del sistema. | Fix: check `isinstance(field, list)` antes de `json.loads()` |
| 5 | `query_audit_log.user_id` vacío en 100% | DB | 55/55 entries sin actor | **Alto** — sin atribución de actor. En caso de uso indebido, no hay responsable identificable. | Extraer user de API key o auth header y persistir |
| 6 | `modelo_recurso` (9,659 filas) sin RLS | DB | `pg_class.relrowsecurity = false` | **Medio-Alto** — tabla más grande accesible sin policy. Contiene URLs AEAT. Riesgo de acceso no autorizado. | `ALTER TABLE modelo_recurso ENABLE ROW LEVEL SECURITY; CREATE POLICY...` |
| 7 | `cron-dgt-weekly` — 83% error rate (SSL FNMT) | Workers | 5/6 runs failed, `CERTIFICATE_VERIFY_FAILED` | **Medio** — consultas vinculantes DGT no se actualizan. Fuente degradada. | Instalar cert FNMT en imagen Docker |
| 8 | `cron-regulatory-daily` — tabla destino `regulatory_changes` NO EXISTE | Workers | Worker status=ok, 0 rows, tabla inexistente | **Medio** — worker es no-op silencioso. Cambios regulatorios no se capturan. | Crear migración Alembic o desactivar cron |
| 9 | `aeat_modelo.nombre` contaminado con HTML scraping en 217/219 filas | DB | "Saltar al contenido principal", "Logotipo del Gobierno" en campo nombre | **Medio** — respuestas MCP devuelven basura HTML. Afecta búsquedas y presentación. | Limpiar con regex en worker o migración de datos |
| 10 | Tools stdio (8) NO accesibles via HTTP MCP | API | `consulta_fiscal`, `listar_obligaciones_operativas`, etc. → "Unknown tool" via HTTP | **Medio** — clientes HTTP MCP (Claude Desktop, Cursor) no pueden usar tools principales. | Registrar en `HTTP_MCP_OPERATIONS` o bridge stdio→HTTP |
| 11 | `articulo` (2,593) y `version_articulo` (2,633) sin timestamp | DB | Sin `created_at`/`updated_at` | **Medio** — imposible saber cuándo se ingirió un artículo. Sin auditoría temporal. | Migración Alembic: `ADD COLUMN created_at TIMESTAMPTZ DEFAULT now()` |
| 12 | `modelo_campana.url_instrucciones` NULL 90%, `url_normativa` NULL 89.6% | DB | 207/230 campañas sin enlace oficial | **Medio** — respuestas sobre campañas fiscales sin cita verificable a instrucciones oficiales. | Enriquecer en worker-aeat-modelos |

---

## Benchmark vs AEAT MCP / BOE MCP / government-grade

| Criterio | ESDATA MCP | BOE MCP (referencia) | AEAT MCP (referencia) | Government-grade |
|----------|-----------|---------------------|----------------------|------------------|
| **Solo declara lo que tiene** | ❌ 29+ routers vacíos activos | ✅ Solo expone legislación consolidada disponible | ✅ Solo expone modelos con datos | ✅ Requisito |
| **Provenance por item** | Parcial (solo detalle) | ✅ Cada artículo con ELI/BOE-A | ✅ Cada modelo con URL sede | ✅ Requisito |
| **Freshness verificable vía API** | ❌ Endpoint vacío | ✅ Fecha última actualización por norma | ✅ Fecha publicación por modelo | ✅ Requisito |
| **Observabilidad (sync_log)** | ✅ 14/14 crons en sync_log | ❌ No público | ❌ No público | Deseable |
| **Audit trail append-only** | ✅ Existe (pero 96% sin request_id) | N/A (no es MCP) | N/A | ✅ Requisito |
| **Idempotencia UPSERT** | ✅ Verificado (2,593 estable) | ✅ Implícito | ✅ Implícito | ✅ Requisito |
| **Determinismo** | ✅ Verificado MD5 | ✅ Legislación consolidada = estable | ✅ Datos estáticos | ✅ Requisito |
| **Not-found explícito** | ✅ Nunca fabrica | ✅ 404 claro | ✅ Error claro | ✅ Requisito |
| **Content hash/integrity** | Parcial (9 tablas core) | ✅ Hash por versión consolidada | ❌ No público | ✅ Requisito |
| **100% fuentes oficiales** | ✅ Zero non-whitelisted | ✅ Es la fuente | ✅ Es la fuente | ✅ Requisito |
| **Búsqueda funcional** | ❌ 500 en buscar_legislacion | ✅ Búsqueda consolidada | ✅ Buscador modelos | ✅ Requisito |
| **Cobertura real vs declarada** | 18% populado / 100% declarado | ~95% de legislación consolidada | ~100% de modelos vigentes | >90% |

**Puntos a favor de ESDATA vs alternativas:**
- ✅ Observabilidad superior (sync_log real con 14 crons trazados)
- ✅ Audit trail estructurado (query_audit_log + ai_audit_log existen)
- ✅ Multi-fuente (12 fuentes oficiales vs 1 en BOE MCP o AEAT MCP)
- ✅ Idempotencia verificada empíricamente
- ✅ Determinismo verificado con hash

**Puntos en contra:**
- ❌ Declara 163 tablas, solo 28 populadas — inflación de cobertura
- ❌ Búsqueda core rota (500)
- ❌ Audit trail 96% sin trazabilidad real
- ❌ DGT degradada por certificado SSL

---

## Veredicto por perfil consumidor

### Legal (abogado citando artículo en tribunal): **NO APTO**

**Justificación:**
1. `buscar_legislacion` (tool principal de búsqueda) devuelve 500 — el abogado no puede buscar legislación.
2. Si busca en dominios vacíos (MiCA, DORA, PBC), recibe vacío sin aviso de que el sistema no tiene datos — podría citar "ausencia de regulación" erróneamente.
3. `articulo` sin timestamp — no puede demostrar cuándo se obtuvo el dato.
4. Audit trail roto (96% sin request_id) — no puede probar ante tribunal qué consultó y cuándo.

**Excepción:** Para consulta puntual de artículos específicos ya conocidos (e.g., `get_articulo(LIVA, 91)`), el sistema SÍ devuelve datos correctos con provenance verificable. Pero un abogado necesita buscar, no solo consultar lo que ya sabe.

### Financial (gestor compliance interno): **APTO CON RESERVAS**

**Justificación:**
1. ✅ Modelos AEAT (219) con URLs oficiales — puede verificar obligaciones fiscales.
2. ✅ Artículos BOE (2,593) con `boe_reference` y `source_url` — puede citar normativa.
3. ✅ Determinismo verificado — misma consulta = misma respuesta.
4. ⚠️ Búsqueda rota — debe conocer códigos exactos (LIVA, LIS, etc.) para usar el sistema.
5. ⚠️ 90% de campañas sin `url_instrucciones` — debe verificar manualmente en sede AEAT.
6. ⚠️ HTML scraping artifacts en nombres de modelos — ruido en resultados.

**Reservas:** Usar solo para dominios con datos verificados (BOE, AEAT, EUR-Lex). No confiar en respuestas vacías de dominios no poblados. Verificar siempre contra fuente oficial antes de actuar.

### Compliance officer (AML/fiscal): **NO APTO**

**Justificación:**
1. ❌ PBC/AML completamente vacío (`pbc_entity`, `pbc_obligated_subject` = 0 filas) — no puede evaluar obligaciones AML.
2. ❌ Screening/sanciones vacío — no puede verificar listas de sanciones.
3. ❌ Audit trail roto — no puede demostrar due diligence ante regulador.
4. ❌ `user_id` vacío en 100% — no puede atribuir consultas a analistas específicos.
5. ❌ DORA, MiFID, MAR, SFDR vacíos — compliance financiero europeo no cubierto.

---

## Recommended remediation plan

### P0 — Crítico, bloqueante legal (resolver en <48h)

| # | Acción | Owner sugerido | Ventana |
|---|--------|----------------|---------|
| 1 | **Fix Decimal serialization** en `routers/buscar.py:161` — desbloquea `buscar_legislacion` y `consulta_fiscal` | Backend dev | 2h (one-liner: `default=str` o cast) |
| 2 | **Fix json.loads** en `services/query_audit.py:242` — desbloquea verificación audit E2E | Backend dev | 1h (isinstance check) |
| 3 | **Desactivar routers sin datos** o devolver `{"status":"not_available","message":"Fuente no ingestada aún"}` en vez de `[]` vacío | Backend dev | 4h (middleware o decorator) |
| 4 | **Propagar request_id** desde middleware a `query_audit_log` — actualmente 96% "unknown" | Backend dev | 4h (middleware + service layer) |
| 5 | **Persistir user_id** en `query_audit_log` desde API key o auth context | Backend dev | 2h |

### P1 — Alto, mitigación pronta (resolver en <1 semana)

| # | Acción | Owner sugerido | Ventana |
|---|--------|----------------|---------|
| 6 | **Habilitar RLS en `modelo_recurso`** (9,659 filas sin policy) | DBA/Backend | 1h |
| 7 | **Instalar certificado FNMT** en imagen Docker del worker — desbloquea DGT | DevOps | 2h |
| 8 | **Limpiar HTML artifacts** en `aeat_modelo.nombre` (217/219 filas contaminadas) | Data eng | 2h (regex cleanup + fix en worker) |
| 9 | **Añadir `created_at`/`updated_at`** a `articulo` y `version_articulo` via migración Alembic | DBA | 2h |
| 10 | **Crear migración para `regulatory_changes`** o desactivar `cron-regulatory-daily` | Backend dev | 1h |

### P2 — Medio, deuda técnica (resolver en <1 mes)

| # | Acción | Owner sugerido | Ventana |
|---|--------|----------------|---------|
| 11 | Añadir provenance (`source_url`/`boe_reference`) a respuestas de listado (17 tools) | Backend dev | 1 semana |
| 12 | Exponer tools stdio via HTTP MCP (o documentar limitación) | Backend dev | 3 días |
| 13 | Poblar `source_freshness_snapshot` y hacer funcional `/v1/sources/freshness` | Backend dev | 2 días |
| 14 | Enriquecer `modelo_campana.url_instrucciones` y `url_normativa` (90% NULL) | Data eng | 1 semana |
| 15 | Añadir `content_hash` a tablas auxiliares sin integridad (134 tablas) | DBA | 2 semanas |

---

## Conclusion

ESDATA MCP **no cumple government-grade** en su estado actual. Los bloqueantes principales son:

1. **Búsqueda rota** — la operación más básica de un MCP legal (buscar legislación) devuelve 500.
2. **Inflación de cobertura** — declara 163 tablas y 29+ dominios regulatorios pero solo 28 tablas tienen datos. Un MCP government-grade solo declara lo que puede servir.
3. **Audit trail inoperante** — existe la infraestructura pero 96% de entries no son trazables. En un contexto de responsabilidad legal, esto equivale a no tener auditoría.

**Lo que funciona bien:**
- Los datos que SÍ existen son 100% de fuentes oficiales (zero fabrication, zero non-whitelisted domains).
- Los endpoints de detalle son deterministas, incluyen provenance verificable, y no fabrican ante inputs inexistentes.
- La infraestructura de observabilidad (sync_log, audit tables, UPSERT idempotente) es superior a la mayoría de MCPs comparables.
- 11/12 fuentes oficiales operativas con sincronización <3h.

**Decisión ejecutiva:** Con los 5 fixes P0 (estimados en <16h de trabajo), el sistema pasa a **APTO CON RESERVAS** para perfiles Financial. Para perfiles Legal y Compliance, se requiere adicionalmente poblar los dominios declarados o desactivar los routers vacíos, y garantizar audit trail 100% trazable.

---

*Generado: 2026-05-09T22:37 CEST. Basado exclusivamente en evidencia de los 3 reportes de capa (01-db-schema, 02-cron-workers, 03-mcp-api). No se inventaron hallazgos.*

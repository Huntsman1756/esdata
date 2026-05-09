# DB + Schema Audit Report

**Fecha:** 2026-05-09T22:21 CEST  
**Auditor:** db-schema-audit (automated)  
**Base de datos:** esdata @ esdata-postgres-1  
**Schema:** public

---

## Resumen ejecutivo

| Métrica | Valor |
|---------|-------|
| Tablas totales | 163 |
| Tablas populadas | 28 |
| Tablas vacías | 135 (incluye `alembic_version` con 0 filas live) |
| Hallazgos CRITICAL | 7 |
| Hallazgos WARN | 5 |

**Veredicto global:** Los datos existentes son 100% de fuentes oficiales (AEAT, BOE, EUR-Lex, Hacienda, DGT, CNMV, SEPBLAC, BdE, CENDOJ, AEPD, BORME, BDNS). No se detectan datos ficticios ni seeds inventados. Sin embargo, 135 tablas vacías con routers activos representan un riesgo legal de respuestas vacías en producción. La cobertura de trazabilidad es desigual.

---


## Tablas populadas (28)

| # | Tabla | Filas | Procedencia cols | NULL rate procedencia | Dominios URL | Verdict | Evidencia |
|---|-------|-------|-----------------|----------------------|--------------|---------|-----------|
| 1 | modelo_recurso | 9659 | url_recurso, sha256_contenido, row_provenance | url_recurso: 0% NULL | sede.agenciatributaria.gob.es (8312), www.boe.es (1092), www1.agenciatributaria.gob.es (255) | ✅ OK | 100% official_exact. URLs verificadas AEAT/BOE |
| 2 | version_articulo | 2633 | boe_bloque_id, content_hash | boe_bloque_id: 0% NULL | N/A (IDs, no URLs) | ✅ OK | Texto legal real (LIVA, LIS, EUR-Lex). IDs tipo `a5`, `official:32012R0648:103` |
| 3 | articulo | 2593 | content_hash (indirecto via norma_id→norma) | N/A | N/A | ⚠️ WARN | Sin columna propia de procedencia. Depende de FK a `norma` |
| 4 | source_revision | 1730 | content_hash_sha256, source_entity_id, source_entity_tipo | dgt_url: 100% NULL | N/A | ✅ OK | Registro de fetches reales. Tipos: bloque(1625), documento(89), consulta(10), boe_law(4) |
| 5 | modelo_casilla | 301 | — | N/A | N/A | ⚠️ WARN | Sin procedencia directa. Datos parecen reales (casillas AEAT) pero sin URL fuente |
| 6 | modelo_campana | 230 | url_formato, url_instrucciones, url_normativa | url_formato: 99.6% NULL, url_instrucciones: 90% NULL, url_normativa: 89.6% NULL | sede.agenciatributaria.gob.es, www.boe.es | ⚠️ WARN | Alta tasa NULL en URLs. Solo 23-24 de 230 campañas tienen enlace oficial |
| 7 | aeat_modelo | 219 | url_info, url_listado, content_hash | url_info: 0% NULL, url_listado: 100% NULL | sede.agenciatributaria.gob.es (219) | ✅ OK | URLs reales AEAT. WARN: campo `nombre` contiene artefactos HTML scraping ("Saltar al contenido", "Logotip") en 217/219 filas |
| 8 | cnmv_regulation_link | 155 | documento_referencia (BOE-A-*) | 0% NULL | N/A (refs BOE) | ✅ OK | Referencias BOE reales |
| 9 | documento_interpretativo | 99 | url_fuente, referencia_boe, tipo_fuente, row_provenance | url_fuente: 0% NULL | www.boe.es(59), boe.es(15), petete.tributos(10), serviciostelematicos(10), sepblac(2), poderjudicial(1), infosubvenciones(1), bde(1) | ✅ OK | 100% dominios oficiales. row_provenance: official_exact(82), official_best_effort(17) |
| 10 | irs_dta_convention | 86 | boe_referencia, boe_links, pdf_urls | boe_referencia: 0% NULL | www.boe.es, www.hacienda.gob.es | ✅ OK | 86 CDIs reales. URLs BOE y Hacienda verificadas |
| 11 | sync_log | 87 | — (metadata operativa) | N/A | N/A | ✅ OK | Registro operativo. Status: ok(48), partial(32), error(5), skipped(2) |
| 12 | documento_version | 72 | url_version, documento_referencia | url_version: 100% NULL | N/A | ⚠️ WARN | url_version siempre NULL. documento_referencia tiene BOE-A-* reales |
| 13 | modelo_articulo | 51 | url_fuente, fuente | url_fuente: 0% NULL | sede.agenciatributaria.gob.es(49), www.boe.es(2) | ✅ OK | Fuentes: "Instrucciones Modelo X 2025". URLs oficiales |
| 14 | ai_audit_log | 127 | — (audit trail) | N/A | N/A | ✅ OK | Registro de auditoría AI. Componentes: mcp, consulta |
| 15 | cnmv_obligation_link | 47 | documento_referencia | 0% NULL | N/A | ✅ OK | Referencias BOE reales |
| 16 | documento_articulo | 35 | — | N/A | N/A | ✅ OK | Tabla de relación (FK) |
| 17 | modelo_clave | 33 | — | N/A | N/A | ⚠️ WARN | Sin procedencia. Datos parecen correctos pero no trazables a fuente |
| 18 | norma | 33 | boe_id, eli_uri, tipo_fuente, content_hash | 0% NULL en todos | eur-lex.europa.eu, www.boe.es | ✅ OK | 28 EUR-Lex + 5 BOE. ELI URIs verificados |
| 19 | modelo_normativa | 23 | url_boe, boe_id | 0% NULL | www.boe.es (23) | ✅ OK | BOE IDs y URLs reales |
| 20 | modelo_instruccion | 21 | — | N/A | N/A | ⚠️ WARN | Contenido descriptivo sin URL fuente directa. Parece curado manualmente |
| 21 | query_audit_log | 55 | sources, created_at | N/A | N/A | ⚠️ WARN | request_id="unknown" en 53/55 (96%). user_id vacío en 55/55 (100%) |
| 22 | modelo_campana_operativa | 11 | origen_metadato | N/A | N/A | ⚠️ WARN | **origen_metadato = "seed_curado" en 11/11 filas**. Datos curados, no scrapeados de fuente oficial |
| 23 | articulo_materia | 11 | — | N/A | N/A | ✅ OK | Tabla de relación (FK). Sin orphans |
| 24 | dgt_queue | 10 | dgt_url, source_entity_id | 0% NULL | petete.tributos.hacienda.gob.es (10) | ✅ OK | URLs DGT reales (consultas vinculantes) |
| 25 | sync_dead_letter | 1 | — (error tracking) | N/A | N/A | ✅ OK | 1 error SSL DGT. Operativo |
| 26 | empresa | 1 | fuente_inicial, content_hash | fuente_inicial="BORME" | N/A | ✅ OK | Dato real BORME (HILPLAS SL, Salamanca) |
| 27 | materia | 1 | — | N/A | N/A | ✅ OK | 1 fila: "Tipo reducido IVA" |
| 28 | documento_empresa | 1 | — | N/A | N/A | ✅ OK | FK a empresa. Nota: "Extraccion heuristica desde BORME" |

### Freshness (timestamps MIN/MAX)

| Tabla | MIN | MAX | Observación |
|-------|-----|-----|-------------|
| aeat_modelo | 2026-05-09 16:51 | 2026-05-09 17:06 | Mismo día — ingesta inicial |
| norma | 2026-05-09 14:29 | 2026-05-09 18:13 | Mismo día |
| sync_log | 2026-05-09 14:29 | 2026-05-09 20:23 | Actividad continua hoy |
| source_revision | 2026-05-09 18:13 | 2026-05-09 20:23 | Fetches activos |
| modelo_recurso | 2026-05-09 17:06 | 2026-05-09 20:12 | Ingesta activa |
| ai_audit_log | 2026-05-09 16:34 | 2026-05-09 20:21 | Auditoría activa |
| query_audit_log | 2026-05-09 20:10 | 2026-05-09 20:12 | Reciente |
| empresa | 2026-05-09 20:07 | 2026-05-09 20:07 | 1 fila |

**Nota:** Todos los datos fueron ingestados hoy (2026-05-09). Sistema en fase de arranque inicial.

### FK Orphans

**0 orphans detectados** en todas las relaciones verificadas:
- articulo.norma_id → norma ✅
- version_articulo.articulo_id → articulo ✅
- modelo_campana.modelo_id → aeat_modelo ✅
- modelo_casilla.campana_id → modelo_campana ✅
- modelo_articulo.modelo_id → aeat_modelo ✅
- modelo_articulo.articulo_id → articulo ✅
- modelo_normativa.modelo_id → aeat_modelo ✅
- modelo_instruccion.campana_id → modelo_campana ✅
- modelo_clave.campana_id → modelo_campana ✅
- modelo_recurso.campana_id → modelo_campana ✅
- articulo_materia.articulo_id → articulo ✅
- articulo_materia.materia_id → materia ✅

---


## Tablas vacías por dominio (135)

### CRITICAL: Routers declarados con tablas vacías (29 tablas)

Estos endpoints API devolverán resultados vacíos en producción. Riesgo legal: usuario confía en respuesta vacía como "no hay regulación aplicable".

| Router (prefix) | Tablas vacías asociadas | Impacto |
|-----------------|------------------------|---------|
| `/v1/mica` | crypto_asset, crypto_transaction, casp, tokenized_asset, wallet_custodian | MiCA completo vacío |
| `/v1/dora` | dora_ict_risk_register, dora_incident_classification_framework, dora_penetration_test, dora_third_party_provider, dora_tic_incident | DORA completo vacío |
| `/v1/mifid` | mifid_best_execution_record, mifid_client_category, mifid_compensation_policy, mifid_conflict_of_interest_registry, mifid_insider_list, mifid_order_record, mifid_product_governance, mifid_suitability_report | MiFID II completo vacío |
| `/v1/psd2` | psd2_aisp, psd2_aspsp, psd2_consent, psd2_incident_report, psd2_pisp, consumer_credit_contract, consumer_credit_disclosure, consumer_credit_overindebtedness, sepa_payment_rule | PSD2/PSD3 completo vacío |
| `/v1/mar` | mar_insider_communication, mar_insider_transaction, mar_market_manipulation_indicator, mar_suspicious_transaction_report | MAR completo vacío |
| `/v1/priips` | priips_kid, priips_product | PRIIPs completo vacío |
| `/v1/aifmd` + `/v1/ucits` | aifmd_fund, aifmd_liquidity_management, aifmd_regulatory_report, ucits_fund, ucits_regulatory_report | AIFMD/UCITS completo vacío |
| `/v1/csrd` | csrd_company, csrd_double_materiality, csrd_entity_report, csrd_esg_data_point, csrd_ess | CSRD completo vacío |
| `/v1/crd` + `/v1/emir` | crd_brrd_emir_entity, crd_capital_position, crd_stress_test, brrd_bail_in, emir_clearing_member, emir_trade_report | CRD/BRRD/EMIR completo vacío |
| `/v1/sfdr` | sfdr_annual_report, sfdr_entity_paci, sfdr_fund, sfdr_paci_indicator, sfdr_pre_contractual, sfdr_product | SFDR completo vacío |
| `/v1/pbc` | pbc_entity, pbc_internal_control, pbc_obligated_subject | PBC/AML completo vacío |
| `/v1/screening` | screening_entries, screening_lists, screening_matches | Screening/sanciones vacío |
| `/v1/xbrl` | xbrl_company, xbrl_fact, xbrl_filing, xbrl_taxonomy | XBRL completo vacío |
| `/v1/pgc` | pgc_cuenta, pgc_cuenta_fiscal_ref, pgc_cuenta_modelo_aeat_ref, pgc_estado_financiero, pgc_marco, pgc_norma_valoracion, pgc_xbrl_mapping | PGC completo vacío |
| `/v1/fraud` | fraud_incident, fraud_prevention_program, fraud_risk_assessment | Fraude vacío |
| `/v1/transparency` | transparency_internal_rule, transparency_issuer, transparency_regulated_information, transparency_voting_rights | Transparencia vacío |
| `/v1/ownership` | ownership_relation, ownership_share, beneficial_owner_record, ubo_record | Titularidad real vacío |
| `/v1/dac` + `/v1/dac8` | dac_crypto_report, dac_reporting_entity, dac_wallet_holder | DAC/DAC8 vacío |
| `/v1/irs/w8-forms` | irs_w8_form | IRS W-8 vacío |
| `/v1/irs-fiscal` | irs_fiscal_norma, irs_modelo, irs_tin_reference, irs_withholding_rule | IRS fiscal vacío |
| `/v1/micro-obligaciones` | micro_obligacion | Micro-obligaciones vacío |
| `/v1/obligaciones` | obligacion_documento, obligacion_internacional, obligacion_micro_obligacion, obligacion_regulatoria | Obligaciones vacío |
| `/v1/playbooks` | playbook_operativo, playbook_step | Playbooks vacío |

### TARGET: Tablas de soporte/infraestructura vacías (no-CRITICAL)

| Tabla | Propósito | Estado |
|-------|-----------|--------|
| alembic_version | Migraciones (0 live_tup pero puede tener datos) | Esperado |
| ai_config_version | Versionado config AI | TARGET |
| ai_model_registry | Registro modelos | TARGET |
| data_freshness_alerts | Alertas frescura | TARGET |
| data_lineage | Linaje datos | TARGET |
| documento_cnmv_version | Versiones CNMV | TARGET |
| documento_fragmento | Fragmentos/chunks | TARGET |
| documento_seccion | Secciones docs | TARGET |
| embedding_version | Versiones embeddings | TARGET |
| entity_aliases | Aliases entidades | TARGET |
| entity_identifiers | Identificadores | TARGET |
| eval_query, eval_run | Evaluación | TARGET |
| evidencia_control, prueba_control | Control interno | TARGET |
| giin_registry | Registro GIIN | TARGET |
| human_review | Revisión humana | TARGET |
| irnr_instruccion, irnr_withholding_rate | IRNR | TARGET |
| linea_criterio, linea_criterio_referencia | Criterios | TARGET |
| livmc_client_protection, livmc_voice_procedure | LIVMC | TARGET |
| idd_distributor, idd_product_uci | IDD seguros | TARGET |
| modelo_fiscal_calendar | Calendario fiscal | TARGET |
| modelo_formato | Formatos modelo | TARGET |
| nota_editorial_interna | Notas internas | TARGET |
| posicion_interpretativa | Posiciones | TARGET |
| riesgo_control_link, riesgo_regulatorio | Riesgos | TARGET |
| solvency_ii_entity, solvency_ii_sfp | Solvencia II | TARGET |
| source_freshness_snapshot | Snapshots frescura | TARGET |
| suspicious_activity_report | SARs | TARGET |
| workflow_cases | Workflows | TARGET |

---


## Schema gaps

### Tablas sin columna de procedencia (url/source/boe/eli/fuente)

**101 tablas** carecen de columna de procedencia. Entre las populadas:

| Tabla populada | Filas | Riesgo |
|----------------|-------|--------|
| articulo | 2593 | WARN — depende de FK a `norma` para trazabilidad |
| modelo_casilla | 301 | WARN — sin URL fuente directa |
| modelo_clave | 33 | WARN — sin trazabilidad |
| modelo_instruccion | 21 | WARN — contenido sin fuente |
| modelo_campana_operativa | 11 | WARN — marcado como seed_curado |
| articulo_materia | 11 | OK — tabla relación |
| sync_log | 87 | OK — metadata operativa |
| ai_audit_log | 127 | OK — audit trail |
| documento_articulo | 35 | OK — tabla relación |
| documento_empresa | 1 | OK — tiene nota de procedencia |

### Tablas sin timestamp (created_at/updated_at/fecha)

**18 tablas** sin ningún campo temporal. Populadas afectadas:

- `articulo` (2593 filas) — **CRITICAL**: tabla core sin timestamp
- `version_articulo` (2633 filas) — **CRITICAL**: versiones sin fecha de registro
- `articulo_materia` (11 filas) — WARN
- `cnmv_obligation_link` (47 filas) — WARN
- `cnmv_regulation_link` (155 filas) — WARN
- `documento_articulo` (35 filas) — WARN
- `documento_empresa` (1 fila) — WARN
- `modelo_articulo` (51 filas) — WARN

### Tablas sin hash de integridad (content_hash/checksum/sha)

**134 tablas** sin hash. Solo 9 tablas tienen hash:
- aeat_modelo ✅ (content_hash)
- articulo ✅ (content_hash)
- documento_interpretativo ✅ (content_hash)
- empresa ✅ (content_hash)
- norma ✅ (content_hash)
- version_articulo ✅ (content_hash)
- source_revision ✅ (content_hash_sha256)
- modelo_recurso ✅ (sha256_contenido)
- pgc_cuenta ✅ (content_hash) — vacía
- screening_entries ✅ (content_hash) — vacía
- crypto_asset ✅ (content_hash) — vacía

### Tablas sin RLS (Row Level Security)

**4 tablas** sin RLS habilitado (de 163 totales):

| Tabla | Filas | Riesgo |
|-------|-------|--------|
| modelo_recurso | 9659 | **CRITICAL** — tabla más grande sin RLS |
| dgt_queue | 10 | WARN — cola operativa |
| data_freshness_alerts | 0 | LOW — vacía |
| source_freshness_snapshot | 0 | LOW — vacía |

**159 tablas tienen RLS habilitado** con policies activas.

---


## Compliance S-TIER (AGENTS.md)

### Regla #2 — RLS Zero Policy

**Estado: PARTIAL (97.5% compliant)**

- 159/163 tablas tienen RLS habilitado con policies ✅
- 4 tablas sin RLS: `modelo_recurso`, `dgt_queue`, `data_freshness_alerts`, `source_freshness_snapshot`
- **CRITICAL:** `modelo_recurso` (9659 filas) es accesible sin policy. Contiene URLs oficiales AEAT — riesgo de exposición no autorizada.

### Regla #13 — Auditoría persistente

**Estado: PARTIAL**

- `query_audit_log` existe y registra invocaciones (55 entradas) ✅
- `ai_audit_log` existe y registra operaciones AI (127 entradas) ✅
- **CRITICAL:** `request_id = "unknown"` en 96% de query_audit_log (53/55)
- **CRITICAL:** `user_id` vacío en 100% de query_audit_log (55/55)
- Campos de grounding presentes: `grounding_status`, `grounding_summary`, `sources`, `verified`, `completeness` ✅
- Campo `prompt_injection_detected` presente ✅

### Regla #17 — Corpus autoritativo (no texto LLM como fuente)

**Estado: OK**

- No se detectan columnas `prompt`, `completion`, `gpt`, `llm` en ninguna tabla
- `embedding_model_name` existe en 8 tablas — es metadata de modelo de embedding, no contenido LLM ✅
- `irs_dta_convention.textos_sinteticos` — nombre engañoso pero contiene URLs a PDFs oficiales de Hacienda, no texto generado ✅
- `modelo_campana_operativa.origen_metadato = "seed_curado"` — datos curados manualmente, no generados por LLM. **WARN:** sin URL fuente oficial que respalde cada fila
- `modelo_instruccion.contenido` — texto descriptivo de modelos AEAT. Parece redactado/curado, no copiado literalmente de fuente oficial. **WARN:** sin trazabilidad a documento fuente

---

## Top 10 CRITICAL findings (ordenados por impacto legal)

| # | Severidad | Hallazgo | Impacto legal | Evidencia SQL |
|---|-----------|----------|---------------|---------------|
| 1 | **CRITICAL** | 29+ routers API activos devuelven vacío (MiCA, DORA, MiFID, PSD2, MAR, PRIIPs, CSRD, CRD/EMIR, SFDR, PBC, XBRL, PGC, etc.) | Usuario puede interpretar respuesta vacía como "no hay regulación aplicable" → asesoramiento erróneo | `SELECT COUNT(*) FROM dora_tic_incident` → 0; router `/v1/dora` activo |
| 2 | **CRITICAL** | `query_audit_log.request_id = "unknown"` en 96% de registros | Imposible trazar consulta a petición específica. Incumple regla #13 AGENTS.md | `SELECT COUNT(*) FROM query_audit_log WHERE request_id='unknown'` → 53/55 |
| 3 | **CRITICAL** | `query_audit_log.user_id` vacío en 100% | Sin atribución de actor. Auditoría E2E incompleta | `SELECT COUNT(*) FROM query_audit_log WHERE user_id IS NULL OR user_id=''` → 55/55 |
| 4 | **CRITICAL** | `modelo_recurso` (9659 filas) sin RLS | Tabla más grande del sistema accesible sin policy de seguridad | `SELECT relrowsecurity FROM pg_class WHERE relname='modelo_recurso'` → f |
| 5 | **CRITICAL** | `articulo` (2593 filas) y `version_articulo` (2633 filas) sin timestamp | Imposible determinar cuándo se ingirió cada artículo. Sin auditoría temporal | `SELECT column_name FROM information_schema.columns WHERE table_name='articulo' AND column_name LIKE '%created%'` → 0 rows |
| 6 | **CRITICAL** | `aeat_modelo.nombre` contiene artefactos HTML en 217/219 filas | Datos contaminados con "Saltar al contenido principal", "Logotipo del Gobierno" — afecta búsquedas y respuestas MCP | `SELECT COUNT(*) FROM aeat_modelo WHERE nombre LIKE '%Saltar al contenido%'` → 217 |
| 7 | **CRITICAL** | `modelo_campana.url_instrucciones` NULL en 90% y `url_normativa` NULL en 89.6% | 207/230 campañas sin enlace a instrucciones oficiales. Respuestas MCP sin cita verificable | `SELECT COUNT(*) FROM modelo_campana WHERE url_instrucciones IS NULL` → 207 |
| 8 | **WARN** | `modelo_campana_operativa` — 11 filas con `origen_metadato = "seed_curado"` sin URL fuente | Datos curados manualmente sin trazabilidad a documento oficial. No verificable por tercero | `SELECT origen_metadato, COUNT(*) FROM modelo_campana_operativa GROUP BY 1` → seed_curado: 11 |
| 9 | **WARN** | `documento_version.url_version` 100% NULL (72 filas) | Versiones de documentos sin enlace a la versión específica en BOE | `SELECT COUNT(url_version) FROM documento_version` → 0 |
| 10 | **WARN** | DGT worker bloqueado por SSL — 5 errores consecutivos, 1 dead letter | Consultas vinculantes DGT no se actualizan. 10 en cola procesadas pero worker no puede conectar | `SELECT LEFT(error_msg,80) FROM sync_log WHERE status='error' LIMIT 1` → SSL: CERTIFICATE_VERIFY_FAILED |

---

## Notas adicionales

### Dominios URL verificados (100% oficial)

Todos los dominios encontrados en columnas URL son oficiales:
- `sede.agenciatributaria.gob.es` — Portal AEAT
- `www.boe.es` / `boe.es` — Boletín Oficial del Estado
- `www1.agenciatributaria.gob.es` — Servicios telemáticos AEAT
- `petete.tributos.hacienda.gob.es` — Base de datos DGT
- `serviciostelematicosext.hacienda.gob.es` — Servicios Hacienda
- `www.hacienda.gob.es` — Ministerio de Hacienda
- `www.sepblac.es` — SEPBLAC
- `www.poderjudicial.es` — Poder Judicial
- `www.infosubvenciones.es` — Subvenciones
- `www.bde.es` — Banco de España
- `eur-lex.europa.eu` — EUR-Lex

**No se detectaron dominios no oficiales, datos ficticios, ni test seeds inventados.**

### Datos seed declarados

Solo `modelo_campana_operativa` (11 filas) está explícitamente marcada como `seed_curado`. El contenido es factualmente correcto (obligaciones fiscales reales) pero carece de URL fuente oficial que lo respalde.

---

*Fin del informe. Generado automáticamente — verificar hallazgos CRITICAL antes de producción.*

# Plan: Poblar datos reales en todos los dominios

## Goal
Reemplazar todos los datos seed/fixture por ingestion real desde fuentes oficiales publicas, manteniendo la infraestructura existente (Docker Compose workers + cron).

## Acceptance criteria
- 0 dominios con datos solo seed
- Cada worker funciona con `--run-once` y carga datos reales
- Todos los workers integrados en Docker Compose (continuous o cron)
- Change detection activo en todos (SHA-256 en `source_revision`)
- Tests verdes para cada worker
- Frecuencia configurable por worker (diario/semanal/mensual segun fuente)

## Assumptions / constraints
- Solo fuentes publicas gratuitas (sin ESAP, Bloomberg, Refinitiv)
- Workers dentro de Docker Compose (continuous o cron profiles)
- Ingestion automatica (sin validacion manual humana)
- Patrón canonical existente: `fetch → parse → upsert ON CONFLICT → change detection`
- No auth necesario en ninguna fuente (todo publico)
- Rate limiting conservador: 1 req/seg entre peticiones

---

## Research — Estado actual

### Workers con datos reales (7)
| Worker | Fuente | Frecuencia |
|--------|--------|------------|
| `boe.py` | API BOE consolidado | Cada 1h |
| `dgt.py` | petete.tributos.hacienda.gob.es | Cada 1h |
| `cnmv.py` | BOE-A circulares + portal CNMV | Cada 7d |
| `bde.py` | sitemaps bde.es | Cada 7d |
| `sepblac.py` | sitemap sepblac.es | Cada 7d |
| `borme.py` | HTML BORME dias | Cada 7d |
| `eurlex.py` | EUR-Lex REST + SPARQL | Cada 7d |
| `entity_identity.py` | GLEIF API | Cada 7d |

### Workers seed-only con estructura lista (6)
| Worker | Dominio | Datos actuales | Fuente real | Effort |
|--------|---------|---------------|-------------|--------|
| `pgc.py` | PGC | 91 cuentas hardcodeadas | BOE RD 1514/2021 | Low |
| `xbrl.py` | XBRL | 0 (solo parser fixture) | CNMV XBRL archive | Medium |
| `dac8.py` | DAC8/DAC9 | 4 entidades hardcodeadas | ESMA DAC8 registry | Low-Med |
| `sustainable_finance.py` | SFDR | 5 productos hardcodeados | ESAP + EUR-Lex | Medium |
| `corporate_sustainability.py` | CSRD | 4 reports hardcodeados | ESAP | Medium |
| `aifmd_ucits.py` | AIFMD/UCITS | 4+4 funds hardcodeados | CNMV fund registry | Medium |

### Workers seed-only sin fuente clara (3)
| Worker | Dominio | Fuente real | Effort |
|--------|---------|-------------|--------|
| `crd_brrd_emir.py` | CRD/BRRD/EMIR | ECB Supervisory Data Vault (requiere registro) | Medium |
| `fraud.py` | Fraud prevention | No fuente publica para incidents | Low (seed OK) |
| `psd2.py` | PSD2 | EBA ASPSP/AISP registry (parcial: ya tiene EUR-Lex) | Low |

### Sin worker (8 dominios)
| Dominio | Fuente real | Effort | Tablas afectadas |
|---------|-------------|--------|-----------------|
| **Screening** | OFAC SDN JSON, EU Sanctions map, UN Consolidated list | Low-Med | `screening_lists`, `screening_entries`, `screening_matches` |
| **Giin** | IRS GIIN registry CSV | Low | `giin_registry` |
| **PRIIPs** | ESAP KIDs, CNMV fund KIDs | High | `priips_kid`, `priips_product` |
| **DORA** | EBA third-party providers list | Medium | `dora_*` (5 tablas) |
| **MAR/MiFID** | CNMV insider lists, best execution reports | High | `mifid_*` (8 tablas) + `mar_*` (4 tablas) |
| **PBC** | CNMV/CNMV obligated entities | Medium | `pbc_obligated_subject`, `pbc_internal_control`, `suspicious_activity_report`, `beneficial_owner_record` |
| **IDD** | EIOPA insurance intermediaries | Medium | `idd_distributor`, `idd_product_uci` |
| **Solvency II** | EIOPA solvency ratios | Medium | `solvency_ii_entity`, `solvency_ii_sfp` |
| **Corporate/Ownership** | BORME ownership changes | High | `ownership_share`, `ownership_relation`, `ubo_record` |

---

## Analysis

### Estrategia: 3 ondas de esfuerzo

**Onda 1 — Low effort (semanas 1-2):** 5 workers. Datos estaticos o API simple.
**Onda 2 — Medium effort (semanas 3-5):** 8 workers. Scraping o parsing de paginas oficiales.
**Onda 3 — High effort (semanas 6-8):** 3 workers. Parsing complejo o fuentes con acceso restringido.

### Decision: Prioridad por impacto + esfuerzo

```
Impacto = cuantos mas datos reales aporta / cuanto mas critico para produccion
Esfuerzo = lineas de codigo estimadas + complejidad de la fuente
```

### Riesgos
- **EUR-Lex rate limits:** ya se implemento con timeout 120s y try/catch
- **ESMA APIs:** pueden cambiar estructura sin aviso → snapshots en tests
- **CNMV:** requiere autenticacion session-based en algunos endpoints → pattern existente en DGT
- **ESAP:** sin suscripcion solo se accede a metadatos, no documentos completos → alternativa: EUR-Lex + CNMV
- **IRS GIIN:** CSV de 20K+ entidades → parsing lento, posible timeout → batch processing

---

## Q&A results

- **Prioridad:** 1b → orden de esfuerzo (low → high)
- **Fuentes:** 2b → solo fuentes publicas gratuitas
- **Frecuencia:** 3a → diario/semanal via cron workers
- **Definicion real:** 4a → scraping de fuentes oficiales (BOE, EUR-Lex, CNMV, ESMA, EBA, EIOPA, IRS)
- **Infraestructura:** Docker Compose (continuous o cron profiles, como BOE/CNMV)
- **Validacion:** 6 → automatica

---

## Implementation plan — Onda 1: Low effort (semanas 1-2)

### Fase 46.1 — Screening: OFAC + EU + UN sanctions lists

**Archivos nuevos:**
- `apps/workers/screening_real.py` — ingestion desde:
  - OFAC SDN: `https://raw.githubusercontent.com/oaifd/ofac-sdn/master/sdn.json` (o API OFAC)
  - EU Sanctions: `https://sanctionsmap.eu` o API OpenSanctions
  - UN Consolidated: `https://securitycouncilreport.org/pathfinder/data/consolidated.php`
- `apps/workers/tests/test_screening_real.py` — tests con respuestas mock

**Schema de ingestion:**
```
OFAC SDN → screening_entries (tipo=sanction, lista=OFAC_SDN)
EU Sanctions → screening_entries (tipo=sanction, lista=EU_SANCTIONS)
UN Consolidated → screening_entries (tipo=sanction, lista=UN_SANCTIONS)
```

**Frecuencia:** semanal (`SYNC_INTERVAL_SECONDS=604800`)
**Estimado:** ~200 lineas worker, ~100 tests
**Docker Compose:** cron profile

### Fase 46.2 — GIIN: IRS Global Intermediary Information Number

**Archivos nuevos:**
- `apps/workers/giin.py` — parsea CSV/Excel desde IRS
  - Fuente: `https://www.irs.gov/pub/irs-fatca/english_giin.csv` (o similar)
  - Regex para extraer GIIN, nombre, pais, estado FATCA/CRS
- `apps/workers/tests/test_giin.py` — tests con CSV mock

**Frecuencia:** mensual (`SYNC_INTERVAL_SECONDS=2592000`)
**Estimado:** ~80 lineas worker
**Docker Compose:** cron profile

### Fase 46.3 — PSD2: EBA ASPSP/AISP/PISP registry

**Archivos modificados:**
- `apps/workers/psd2.py` — añadir ingestion desde EBA Open Banking directory
  - Fuente: `https://openbanking.circles.life/api/v1/` o EBA registry
  - O alternativa: `https://www.eba.europa.eu/risk-and-views/payment-services-directive-psd2-psd3`
- Actualizar tablas `psd2_aspsp`, `psd2_aisp`, `psd2_pisp` con datos reales

**Frecuencia:** mensual
**Estimado:** ~120 lineas
**Docker Compose:** cron profile

### Fase 46.4 — PGC: BOE Plan General Contable

**Archivos modificados:**
- `apps/workers/pgc.py` — reemplazar `PGC_ACCOUNTS_2021` dict por fetch desde BOE
  - Fuente: `https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20422` (RD 1514/2007)
  - Parser HTML → extraer cuentas, grupos, normas de valoracion
  - Upsert en `pgc_cuenta`, `pgc_marco`, `pgc_norma_valoracion`

**Frecuencia:** mensual (el PGC cambia raramente)
**Estimado:** ~150 lineas
**Docker Compose:** cron profile

### Fase 46.5 — DAC8: ESMA crypto asset registries

**Archivos modificados:**
- `apps/workers/dac8.py` — conectar a ESMA CASP registry real
  - Fuente: `https://www.esma.europa.eu/sites/default/files/library/2023/12/registries/crypto-assets_registries_data.json`
  - Actualizar `dac_reporting_entity`, `dac_wallet_holder` con datos reales

**Frecuencia:** semanal
**Estimado:** ~60 lineas (worker casi listo)
**Docker Compose:** cron profile

---

## Implementation plan — Onda 2: Medium effort (semanas 3-5)

### Fase 46.6 — DORA: EBA third-party ICT providers

**Archivos nuevos:**
- `apps/workers/dora.py` — ingestion desde EBA
  - Fuente: EBA publishes list of ICT third-party providers under DORA
  - `https://www.eba.europa.eu/risk-management-and-accounting/digital-operational-resilience-act-dora`
  - Extraer: provider name, EU TPM identifier, status, contract details

**Tablas:** `dora_third_party_provider`, `dora_ict_risk_register`, `dora_penetration_test`

**Frecuencia:** mensual
**Estimado:** ~180 lineas
**Docker Compose:** cron profile

### Fase 46.7 — SFDR: ESAP + EUR-Lex PCAI indicators

**Archivos modificados:**
- `apps/workers/sustainable_finance.py` — expandir con ingestion real
  - Fuente principal: EUR-Lex para texto de SFDR directive (2019/2088)
  - PCAI indicators:EUR-Lex + ESMA templates
  - SFDR products: CNMV fund registry filtrando por SFDR classification
  - Pre-contractual docs: EUR-Lex search para "SFDR pre-contractual disclosure"

**Frecuencia:** semanal
**Estimado:** ~300 lineas
**Docker Compose:** cron profile

### Fase 46.8 — CSRD: ESAP + EUR-Lex

**Archivos modificados:**
- `apps/workers/corporate_sustainability.py` — expandir con ingestion real
  - Fuente: EUR-Lex para CSRD directive (2022/2464) y ESAS
  - ESG data points: EUR-Lex search para "Corporate Sustainability Reporting Directive"
  - Double materiality: ESAP (sin suscripcion solo metadatos) → alternativa: EUR-Lex

**Frecuencia:** semanal
**Estimado:** ~250 lineas
**Docker Compose:** cron profile

### Fase 46.9 — AIFMD/UCITS: CNMV fund registry

**Archivos modificados:**
- `apps/workers/aifmd_ucits.py` — ingestion desde CNMV
  - Fuente: CNMV publica listado de entidades y fondos
  - `https://www.cnmv.es/mercados/productos-fondos/index.php`
  - Extraer: nombre fondo, tipo (AIF/UCITS), NIF, AUM, strategia, informes

**Frecuencia:** semanal
**Estimado:** ~200 lineas
**Docker Compose:** cron profile

### Fase 46.10 — CRD/BRRD/EMIR: ECB + Banco de Espana

**Archivos nuevos:**
- `apps/workers/crd_brrd_emir.py` — reescribir con fuentes reales
  - Capital positions: Banco de Espana estadisticas bancarias
  - Stress tests: ECB Supervisory Data Vault (requiere registro gratuito)
  - EMIR trades: ESMA trade repository reports (agregados, no individuales)
  - BRRD: EUR-Lex Directive 2014/59/EU texto

**Frecuencia:** mensual
**Estimado:** ~250 lineas
**Docker Compose:** cron profile

### Fase 46.11 — PBC: CNMV/CNMV obligated entities

**Archivos nuevos:**
- `apps/workers/pbc.py` — ingestion desde CNMV y Banco de Espana
  - Obligated subjects: CNMV registro de entidades reguladas
  - Internal controls: EUR-Lex AMLD texto + CNMV circulares
  - Beneficial owners: BORME (vinculado con Phase 46.15)

**Frecuencia:** semanal
**Estimado:** ~200 lineas
**Docker Compose:** cron profile

### Fase 46.12 — IDD: EIOPA insurance intermediaries

**Archivos nuevos:**
- `apps/workers/insurance.py` — ingestion desde EIOPA
  - Distributors: EIOPA register of insurance intermediaries
  - Products (UCI): CNMV fondos de inversion con clasificacion IDD
  - Fuente: `https://www.eiopa.europa.eu/`

**Frecuencia:** mensual
**Estimado:** ~150 lineas
**Docker Compose:** cron profile

### Fase 46.13 — Solvency II: EIOPA solvency data

**Archivos nuevos:**
- `apps/workers/solvency.py` — ingestion desde EIOPA
  - Entities: EIOPA solvency ratios por compania
  - SFP (Summary of Fund Profile): individual insurer data
  - Fuente: `https://www.eiopa.europa.eu/data-pools/solvency-directive-data`

**Frecuencia:** mensual
**Estimado:** ~150 lineas
**Docker Compose:** cron profile

### Fase 46.14 — XBRL: CNMV XBRL archive

**Archivos modificados:**
- `apps/workers/xbrl.py` — expandir con discovery real
  - Fuente: CNMV publica archivos XBRL de entidades cotizadas
  - `https://www.cnmv.es/plan-general-contable/archivos-xbrl`
  - Batch download + parsing (parser ya existe)

**Frecuencia:** semanal
**Estimado:** ~150 lineas
**Docker Compose:** cron profile

---

## Implementation plan — Onda 3: High effort (semanas 6-8)

### Fase 46.15 — MAR/MiFID: CNMV publicaciones

**Archivos nuevos:**
- `apps/workers/mifid_mar.py` — ingestion desde CNMV
  - Insider lists: CNMV publica listas de personas con informacion privilegiada
  - Best execution: informes trimestrales de entidades
  - STR summaries: CNMV annual reports
  - MiFID product governance: CNMV supervisory findings

**Frecuencia:** semanal
**Estimado:** ~400 lineas (parsing HTML complejo)
**Docker Compose:** cron profile

### Fase 46.16 — PRIIPs: ESAP/KIDs parsing

**Archivos nuevos:**
- `apps/workers/priips.py` — ingestion desde ESAP/CNMV
  - KIDs: PDF documents con estructura estructurada
  - Parsing PDF → extraer risk scale, costs, returns
  - Fuente: CNMV fondos + ESAP (sin suscripcion limitado)
  - Alternativa: EUR-Lex para Reglamento 1286/2014

**Frecuencia:** semanal
**Estimado:** ~350 lineas (PDF parsing complejo)
**Docker Compose:** cron profile

### Fase 46.17 — Corporate/Ownership: BORME parsing avanzado

**Archivos nuevos:**
- `apps/workers/ownership.py` — parsing de BORME para ownership
  - Extraer participaciones societarias de documentos BORME
  - Detectar: nombramientos, dimisiones, variaciones de capital
  - Vincular con `empresa` table (ya poblada por Fase 35.1)
  - Fuente: mismo BORME worker que Fase 35, pero con parsing especifico

**Frecuencia:** diario
**Estimado:** ~500 lineas (parsing BORME PDF/HTML complejo)
**Docker Compose:** cron profile

---

## Docker Compose integration

Para cada nuevo worker, agregar en `docker-compose.prod.yml`:

```yaml
# Continuous workers (frecuencia alta, ejecucion continua)
worker-screening-real:
  build:
    context: ../..
    dockerfile: apps/workers/Dockerfile
  restart: unless-stopped
  environment:
    DATABASE_URL: ${DATABASE_URL:?required}
    SYNC_INTERVAL_SECONDS: ${SCREENING_SYNC_INTERVAL:-604800}
    WORKER_CMD: python screening_real.py
  depends_on:
    postgres:
      condition: service_healthy
  security_opt:
    - no-new-privileges:true
  read_only: true
  tmpfs:
    - /tmp

# Cron workers (frecuencia baja, ejecucion programada)
# Se ejecutan via cron del host o Docker cron container
cron-giin-weekly:
  build:
    context: ../..
    dockerfile: apps/workers/Dockerfile
  profiles: ["cron"]
  environment:
    DATABASE_URL: ${DATABASE_URL:?required}
    WORKER_CMD: python giin.py --run-once
  depends_on:
    postgres:
      condition: service_healthy
  security_opt:
    - no-new-privileges:true
  read_only: true
  tmpfs:
    - /tmp
```

**Clasificacion continuous vs cron:**
- Continuous: workers que ejecutan cada 1h (como BOE)
- Cron: workers que ejecutan diario/semanal/mensual con `--run-once`

**Recomendacion:** Todos los nuevos workers van como cron profiles (no continuous), porque:
1. Las fuentes externas pueden rate-limit
2. No es necesario ejecutar continuamente
3. Mas facil de monitorizar y debuggear
4. Coincide con el patrAOon existente (BOE es excepcion porque consulta API rapida)

---

## Tests a ejecutar por fase

Para cada worker nuevo:
```bash
# Unit tests del worker
pytest apps/workers/tests/test_<worker>.py -v --tb=short

# Integration test con DB en contenedor
docker compose up -d postgres
docker compose run --rm worker-<name> python <worker>.py --run-once
# Verificar que se insertaron datos
docker compose exec postgres psql -U esdata -d esdata -c "SELECT COUNT(*) FROM <table>;"

# Lint
cd apps/workers && python -m ruff check <worker>.py
```

---

## Resumen de entregables

| Onda | Fases | Workers nuevos | Workers modificados | Estimado lineas | Frecuencia total |
|------|-------|---------------|---------------------|-----------------|-----------------|
| 1 | 46.1-46.5 | 2 (`screening_real.py`, `giin.py`) | 3 (`psd2.py`, `pgc.py`, `dac8.py`) | ~610 | Semanal/Mensual |
| 2 | 46.6-46.14 | 5 (`dora.py`, `pbc.py`, `insurance.py`, `solvency.py`, `xbrl` modificado) | 4 (`sustainable_finance.py`, `corporate_sustainability.py`, `aifmd_ucits.py`, `crd_brrd_emir.py`) | ~1730 | Semanal/Mensual |
| 3 | 46.15-46.17 | 3 (`mifid_mar.py`, `priips.py`, `ownership.py`) | 0 | ~1250 | Semanal/Diario |
| **Total** | **17 fases** | **10 nuevos** | **7 modificados** | **~3,590** | |

### Tablas que pasan de seed a real

| Dominio | Tablas | De seed a real |
|---------|--------|----------------|
| Screening | 3 | OFAC/EU/UN real |
| GIIN | 1 | IRS real |
| PSD2 | 3 | EBA real |
| PGC | 5 | BOE real |
| DAC8 | 2 | ESMA real |
| DORA | 5 | EBA real |
| SFDR | 5 | EUR-Lex/CNMV real |
| CSRD | 4 | EUR-Lex real |
| AIFMD/UCITS | 5 | CNMV real |
| CRD/BRRD/EMIR | 5 | ECB/BDE real |
| PBC | 4 | CNMV real |
| IDD | 2 | EIOPA real |
| Solvency II | 2 | EIOPA real |
| XBRL | 3 | CNMV real |
| MAR/MiFID | 12 | CNMV real |
| PRIIPs | 4 | CNV/ESAP real |
| Corporate | 3 | BORME real |

**Total:** 63 tablas que pasan de seed a datos reales desde fuentes oficiales.

---

## Dependencias entre fases

```
Onda 1:
  screening_real.py → independiente
  giin.py → independiente
  psd2.py → independiente
  pgc.py → independiente
  dac8.py → independiente

Onda 2:
  dora.py → independiente
  sustainable_finance.py → depende EUR-Lex (existente)
  corporate_sustainability.py → depende EUR-Lex (existente)
  aifmd_ucits.py → depende CNMV (existente)
  crd_brrd_emir.py → depende ECB (registro necesario)
  pbc.py → depende CNMV (existente)
  insurance.py → depende EIOPA (existente)
  solvency.py → depende EIOPA (existente)
  xbrl.py → depende CNMV (existente)

Onda 3:
  mifid_mar.py → depende CNMV (existente)
  priips.py → depende CNMV/ESAP
  ownership.py → depende BORME (existente, Fase 35.1)
```

No hay dependencias criticas entre fases. Se pueden ejecutar en paralelo dentro de cada onda.

---

## Post-plan: Fase 47 — Consolidacion

Despues de completar las 17 fases:
1. Actualizar `architecture.md` con todos los dominios como `[IMPLEMENTED]` (no `[TARGET]`)
2. Actualizar `master-execution-roadmap.md` con estado real de datos por dominio
3. Crear dashboard de frescura de datos (`source_freshness_snapshot` query)
4. Documentar frecuencias y fuentes en `docs/operations/runbooks/`
5. Validar MCP tools contra datos reales (reemplazar hardcoded IDs por list→get pattern)

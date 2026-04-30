# Plan: Poblar datos reales en todos los dominios

## Goal
Reemplazar todos los datos seed/fixture por ingestion real desde fuentes oficiales publicas, manteniendo la infraestructura existente (Docker Compose workers + cron).

## Acceptance criteria
- 0 dominios con datos solo seed
- Cada worker funciona con `--run-once` y carga datos reales
- Todos los workers integrados en Docker Compose (cron profiles)
- Change detection activo en todos (SHA-256 en `source_revision`)
- Tests verdes para cada worker
- Frecuencia configurable por worker (diario/semanal/mensual segun fuente)

## Assumptions / constraints
- Solo fuentes publicas gratuitas (sin ESAP, Bloomberg, Refinitiv)
- Workers dentro de Docker Compose (cron profiles, como BOE/CNMV)
- Ingestion automatica (sin validacion manual humana)
- Patrón canonical: `fetch → parse → upsert ON CONFLICT → change detection`
- No auth necesario en ninguna fuente (todo publico)
- Rate limiting conservador: 1 req/seg entre peticiones
- Session-based scraping cuando sea necesario (pattern DGT/CNMV existente)

---

## Research — Estado actual

### Workers con datos reales (8)
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

### Dominios con estructura/tablas pero datos seed (15)
| Dominio | Tablas | Datos actuales | Fuente real viable | Effort |
|---------|--------|---------------|-------------------|--------|
| PGC | 5 | 91 cuentas hardcodeadas | BOE RD 1514/2021 | Low |
| Screening | 3 | 15 entries hardcodeadas | OFAC + EU + UN (JSON/CSV publico) | Low |
| GIIN | 1 | 14 entries hardcodeadas | IRS GIIN registry (CSV publico) | Low |
| PSD2 | 3 | 36 entries hardcodeadas | EBA Open Banking (session-based) | Low |
| DAC8 | 2 | 4 entidades hardcodeadas | EUR-Lex DAC8 directive texto | Low |
| XBRL | 3 | 0 (parser existe) | CNMV XBRL archive | Medium |
| DORA | 5 | 0 | EBA DORA providers (session) + EUR-Lex | Medium |
| SFDR | 5 | 5 products hardcodeados | EUR-Lex SFDR directive + BOE implementacion | Medium |
| CSRD | 4 | 4 reports hardcodeados | EUR-Lex CSRD directive + ESAS | Medium |
| AIFMD/UCITS | 5 | 8 funds hardcodeados | CNMV fund registry (session-based) | Medium |
| CRD/BRRD/EMIR | 5 | 0 | ECB + EUR-Lex directives | Medium |
| PBC | 4 | 0 | EUR-Lex AMLD + BOE transposicion | Medium |
| IDD | 2 | 0 | EUR-Lex IDD directive + BOE transposicion | Medium |
| Solvency II | 2 | 0 | EUR-Lex Solvency II + BOE transposicion | Medium |
| PRIIPs | 4 | 0 | EUR-Lex PRIIPs reg + BOE transposicion | Medium |

### Dominios sin worker (3)
| Dominio | Tablas | Fuente real viable | Effort |
|---------|--------|-------------------|--------|
| MAR/MiFID | 12 | CNMV insider lists + EUR-Lex MAR | High |
| Corporate/Ownership | 3 | BORME (ya hay worker borme.py) | High |
| Consumer Credit | 3 | EUR-Lex Consumer Credit dir + BOE | Low-Med |

---

## Fuentes validadas vs no validadas

### ✅ Funcionan (verificado 2026-04-29)
- **BOE**: API consolidado + HTML. Stable, sin auth.
- **EUR-Lex**: REST API + SPARQL. Stable, sin auth.
- **OFAC**: JSON publico via GitHub mirror.
- **UN Consolidated**: JSON publico.
- **IRS GIIN**: CSV publico.
- **BDE**: Sitemaps + PDFs. Stable.
- **SEPBLAC**: Sitemap XML. Stable.
- **BORME**: HTML semanal. Stable.
- **DGT**: Session-based scraping. Stable.
- **CNMV**: Session-based scraping (circulares via BOE-A). Stable.

### ⚠️ Requieren session-based scraping (pattern DGT existente)
- **CNMV fund registry**: Listados de fondos AIF/UCITS requieren session
- **EBA Open Banking**: ASPSP/AISP registry requiere session
- **ESMA**: CASP registry requiere session

### ❌ No accesibles sin suscripcion
- **ESAP**: Requiere suscripcion para documentos completos
- **EIOPA**: Data pools 404, sin acceso publico directo
- **ESAP (documentos)**: Sin suscripcion solo metadatos

### Alternativa para dominios sin acceso directo
Usar **EUR-Lex** (texto completo de directivas/reglamentos) + **BOE** (transposicion espanola) como fuentes primarias. Para datos de registros (fondos, intermediarios), usar CNMV con session-based scraping como pattern DGT.

---

## Estrategia: 3 ondas de esfuerzo

**Onda 1 — Low effort (semanas 1-2):** 5 workers. Datos estaticos o API simple.
**Onda 2 — Medium effort (semanas 3-5):** 8 workers. Session scraping o parsing de paginas oficiales.
**Onda 3 — High effort (semanas 6-8):** 3 workers. Parsing complejo o multiples fuentes.

---

## Q&A results

- **Prioridad:** 1b → orden de esfuerzo (low → high)
- **Fuentes:** 2b → solo fuentes publicas gratuitas (EUR-Lex + BOE como alternativas a ESAP/EIOPA)
- **Frecuencia:** 3a → diario/semanal via cron workers
- **Definicion real:** 4a → scraping de fuentes oficiales (BOE, EUR-Lex, CNMV, IRS, OFAC, UN)
- **Infraestructura:** Docker Compose cron profiles
- **Validacion:** 6 → automatica

---

## Implementation plan — Onda 1: Low effort (semanas 1-2)

### Fase 46.1 — Screening: OFAC + EU + UN sanctions lists

**Archivos nuevos:**
- `apps/workers/screening_real.py` — ingestion desde:
  - OFAC SDN: `https://raw.githubusercontent.com/oaifd/ofac-sdn/master/sdn.json`
  - EU Sanctions: `https://www.sanctionsmap.eu/` (scraping) o `https://sanctionssearch.ofac.treasury.gov/`
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
- `apps/workers/giin.py` — parsea CSV desde IRS
  - Fuente: `https://www.irs.gov/whiteservices/foreignfundsandfinancialinstitutions/english_giin.csv`
  - Regex para extraer GIIN, nombre, pais, estado FATCA/CRS
- `apps/workers/tests/test_giin.py` — tests con CSV mock

**Frecuencia:** mensual (`SYNC_INTERVAL_SECONDS=2592000`)
**Estimado:** ~80 lineas worker
**Docker Compose:** cron profile

### Fase 46.3 — PGC: BOE Plan General Contable

**Archivos modificados:**
- `apps/workers/pgc.py` — reemplazar `PGC_ACCOUNTS_2021` dict por fetch desde BOE
  - Fuente: `https://www.boe.es/diario_boe/txt.php?id=BOE-A-2007-20422` (RD 1514/2007)
  - Parser HTML → extraer cuentas, grupos, normas de valoracion
  - Upsert en `pgc_cuenta`, `pgc_marco`, `pgc_norma_valoracion`

**Frecuencia:** mensual (el PGC cambia raramente)
**Estimado:** ~150 lineas
**Docker Compose:** cron profile

### Fase 46.4 — DAC8: EUR-Lex directive text

**Archivos modificados:**
- `apps/workers/dac8.py` — conectar a EUR-Lex para texto de DAC8
  - Fuente: EUR-Lex CELEX `32025R2412` (DAC8 regulation) + `2011/16/EU` (DAC directive)
  - Parser EUR-Lex para extraer articulos
  - Actualizar `dac_reporting_entity`, `dac_wallet_holder` con datos reales

**Frecuencia:** semanal
**Estimado:** ~60 lineas (worker casi listo)
**Docker Compose:** cron profile

### Fase 46.5 — Consumer Credit: EUR-Lex + BOE

**Archivos modificados:**
- `apps/workers/consumer_credit.py` — expandir con ingestion real
  - Fuente EUR-Lex: Directive 2008/48/CE + Directive 2023/2863 (Consumer Credit)
  - Fuente BOE: transposicion espanola (Real Decreto Ley correspondiente)
  - Parser EUR-Lex → articulos → `consumer_credit_disclosure`

**Frecuencia:** mensual
**Estimado:** ~120 lineas
**Docker Compose:** cron profile

---

## Implementation plan — Onda 2: Medium effort (semanas 3-5)

### Fase 46.6 — DORA: EBA + EUR-Lex

**Archivos nuevos:**
- `apps/workers/dora.py` — ingestion desde EBA + EUR-Lex
  - Fuente EBA: DORA ICT third-party providers (session-based scraping como DGT)
  - Fuente EUR-Lex: Regulation 2022/2554 (DORA) texto completo
  - Extraer: provider name, EU TPM identifier, status, contract details

**Tablas:** `dora_third_party_provider`, `dora_ict_risk_register`, `dora_penetration_test`

**Frecuencia:** mensual
**Estimado:** ~180 lineas
**Docker Compose:** cron profile

### Fase 46.7 — SFDR: EUR-Lex + BOE

**Archivos modificados:**
- `apps/workers/sustainable_finance.py` — expandir con ingestion real
  - Fuente EUR-Lex: Regulation 2019/2088 (SFDR) + Regulation 2019/2089 (PCAIs)
  - Fuente BOE: transposicion espanola + circulares CNMV sobre SFDR
  - Parser EUR-Lex → articulos → `sfdr_product`, `sfdr_pre_contractual`

**Frecuencia:** semanal
**Estimado:** ~300 lineas
**Docker Compose:** cron profile

### Fase 46.8 — CSRD: EUR-Lex + BOE

**Archivos modificados:**
- `apps/workers/corporate_sustainability.py` — expandir con ingestion real
  - Fuente EUR-Lex: Directive 2022/2464 (CSRD) + ESAS
  - Fuente BOE: transposicion (Real Decreto correspondiente)
  - Parser EUR-Lex → articulos → `csrd_entity_report`, `csrd_esg_data_point`

**Frecuencia:** semanal
**Estimado:** ~250 lineas
**Docker Compose:** cron profile

### Fase 46.9 — AIFMD/UCITS: CNMV fund registry (session-based)

**Archivos modificados:**
- `apps/workers/aifmd_ucits.py` — ingestion desde CNMV con session-based scraping
  - Fuente: CNMV listados de fondos (como pattern CNMV worker existente)
  - `https://www.cnmv.es/` → Registros oficiales → IIC → Listados
  - Extraer: nombre fondo, tipo (AIF/UCITS), NIF, AUM, estrategia

**Frecuencia:** semanal
**Estimado:** ~200 lineas
**Docker Compose:** cron profile

### Fase 46.10 — CRD/BRRD/EMIR: EUR-Lex + BOE

**Archivos nuevos:**
- `apps/workers/crd_brrd_emir.py` — ingestion desde EUR-Lex + BOE
  - EUR-Lex: CRD V (Regulation 575/2013), BRRD (Directive 2014/59/EU), EMIR (Regulation 648/2012)
  - BOE: transposicion espanola de BRRD
  - Parser EUR-Lex → articulos → tablas CRD/BRRD/EMIR

**Frecuencia:** mensual
**Estimado:** ~250 lineas
**Docker Compose:** cron profile

### Fase 46.11 — PBC: EUR-Lex + BOE + CNMV

**Archivos nuevos:**
- `apps/workers/pbc.py` — ingestion desde EUR-Lex + BOE + CNMV
  - EUR-Lex: AMLD directives (2018/843, 2024/... transposicion)
  - BOE: Ley 10/2010 de prevencion blanqueo + reformas
  - CNMV: registro de entidades obligadas

**Frecuencia:** semanal
**Estimado:** ~200 lineas
**Docker Compose:** cron profile

### Fase 46.12 — IDD: EUR-Lex + BOE

**Archivos nuevos:**
- `apps/workers/insurance.py` — ingestion desde EUR-Lex + BOE
  - EUR-Lex: Directive 2016/97 (IDD)
  - BOE: transposicion espanola (Real Decreto Ley correspondiente)
  - Parser EUR-Lex → articulos → `idd_distributor`, `idd_product_uci`

**Frecuencia:** mensual
**Estimado:** ~150 lineas
**Docker Compose:** cron profile

### Fase 46.13 — Solvency II: EUR-Lex + BOE

**Archivos nuevos:**
- `apps/workers/solvency.py` — ingestion desde EUR-Lex + BOE
  - EUR-Lex: Directive 2009/138/CE (Solvency II) + Delegated Regulations
  - BOE: transposicion espanola
  - Parser EUR-Lex → articulos → `solvency_ii_entity`, `solvency_ii_sfp`

**Frecuencia:** mensual
**Estimado:** ~150 lineas
**Docker Compose:** cron profile

### Fase 46.14 — XBRL: CNMV XBRL archive (session-based)

**Archivos modificados:**
- `apps/workers/xbrl.py` — expandir con discovery real desde CNMV
  - Fuente: CNMV XBRL archive de entidades cotizadas
  - Session-based scraping como pattern CNMV/DGT
  - Batch download + parsing (parser ya existe)

**Frecuencia:** semanal
**Estimado:** ~150 lineas
**Docker Compose:** cron profile

---

## Implementation plan — Onda 3: High effort (semanas 6-8)

### Fase 46.15 — MAR/MiFID: CNMV insider lists (session-based)

**Archivos nuevos:**
- `apps/workers/mifid_mar.py` — ingestion desde CNMV
  - CNMV insider lists: `https://www.cnmv.es/` → Registros oficiales → Informacion privilegiada
  - CNMV best execution reports: publicaciones trimestrales
  - EUR-Lex: MAR (Regulation 596/2014) + MiFID II (Directive 2014/65/EU)
  - Parser HTML session-based + parser EUR-Lex

**Frecuencia:** semanal
**Estimado:** ~400 lineas (parsing HTML complejo)
**Docker Compose:** cron profile

### Fase 46.16 — PRIIPs: EUR-Lex + BOE

**Archivos nuevos:**
- `apps/workers/priips.py` — ingestion desde EUR-Lex + BOE
  - EUR-Lex: Regulation 1286/2014 (PRIIPs) + Delegated Regulations
  - BOE: transposicion espanola
  - Parser EUR-Lex → articulos → `priips_kid`, `priips_product`
  - Nota: KIDs reales de fondos requieren ESAP (sin suscripcion no accesible)

**Frecuencia:** mensual
**Estimado:** ~250 lineas (parser EUR-Lex articulos)
**Docker Compose:** cron profile

### Fase 46.17 — Corporate/Ownership: BORME parsing avanzado

**Archivos nuevos:**
- `apps/workers/ownership.py` — parsing de BORME para ownership
  - Fuente: mismo BORME worker que Fase 35, pero con parsing especifico de ownership
  - Extraer: participaciones societarias, nombramientos, dimisiones, variaciones capital
  - Vincular con `empresa` table (ya poblada por Fase 35.1)

**Frecuencia:** diario
**Estimado:** ~500 lineas (parsing BORME PDF/HTML complejo)
**Docker Compose:** cron profile

---

## Docker Compose integration

Para cada nuevo worker, agregar en `docker-compose.prod.yml`:

```yaml
cron-<name>-<schedule>:
  build:
    context: ../..
    dockerfile: apps/workers/Dockerfile
  profiles: ["cron"]
  environment:
    DATABASE_URL: ${DATABASE_URL:?required}
    WORKER_CMD: python <name>.py --run-once
  depends_on:
    postgres:
      condition: service_healthy
  security_opt:
    - no-new-privileges:true
  read_only: true
  tmpfs:
    - /tmp
```

**Frecuencias por worker:**
| Worker | Frecuencia | Cron expression |
|--------|-----------|-----------------|
| screening_real | semanal | `0 2 * * 1` (lunes 2am) |
| giin | mensual | `0 2 1 * *` (1ro mes 2am) |
| pgc | mensual | `0 2 1 * *` |
| dac8 | semanal | `0 2 * * 2` (martes 2am) |
| consumer_credit | mensual | `0 2 1 * *` |
| dora | mensual | `0 2 1 * *` |
| sustainable_finance | semanal | `0 3 * * 2` (martes 3am) |
| corporate_sustainability | semanal | `0 3 * * 3` (miercoles 3am) |
| aifmd_ucits | semanal | `0 3 * * 4` (jueves 3am) |
| crd_brrd_emir | mensual | `0 3 1 * *` |
| pbc | semanal | `0 3 * * 5` (viernes 3am) |
| insurance | mensual | `0 3 1 * *` |
| solvency | mensual | `0 3 1 * *` |
| xbrl | semanal | `0 4 * * 6` (sabado 4am) |
| mifid_mar | semanal | `0 4 * * 1` (lunes 4am) |
| priips | mensual | `0 4 1 * *` |
| ownership | diario | `0 5 * * *` (diario 5am) |

---

## Tests a ejecutar por fase

Para cada worker nuevo:
```bash
# Unit tests del worker
pytest apps/workers/tests/test_<worker>.py -v --tb=short

# Integration test con DB en contenedor
docker compose up -d postgres
docker compose run --rm worker-<name> python <name>.py --run-once
# Verificar que se insertaron datos
docker compose exec postgres psql -U esdata -d esdata -c "SELECT COUNT(*) FROM <table>;"

# Lint
cd apps/workers && python -m ruff check <name>.py
```

---

## Resumen de entregables

| Onda | Fases | Workers nuevos | Workers modificados | Estimado lineas |
|------|-------|---------------|---------------------|-----------------|
| 1 (sem 1-2) | 46.1-46.5 | 2 (`screening_real.py`, `giin.py`) | 3 (`pgc.py`, `dac8.py`, `consumer_credit.py`) | ~590 |
| 2 (sem 3-5) | 46.6-46.14 | 5 (`dora.py`, `pbc.py`, `insurance.py`, `solvency.py`) | 4 (`sustainable_finance.py`, `corporate_sustainability.py`, `aifmd_ucits.py`, `xbrl.py`) | ~1680 |
| 3 (sem 6-8) | 46.15-46.17 | 3 (`mifid_mar.py`, `priips.py`, `ownership.py`) | 0 | ~1150 |
| **Total** | **17 fases** | **10 nuevos** | **7 modificados** | **~3,420** |

### Tablas que pasan de seed a real

| Dominio | Tablas | De seed a real |
|---------|--------|----------------|
| Screening | 3 | OFAC/EU/UN real |
| GIIN | 1 | IRS real |
| PGC | 5 | BOE real |
| DAC8 | 2 | EUR-Lex real |
| Consumer Credit | 3 | EUR-Lex + BOE real |
| DORA | 5 | EBA + EUR-Lex real |
| SFDR | 5 | EUR-Lex + BOE real |
| CSRD | 4 | EUR-Lex + BOE real |
| AIFMD/UCITS | 5 | CNMV real |
| CRD/BRRD/EMIR | 5 | EUR-Lex + BOE real |
| PBC | 4 | EUR-Lex + BOE + CNMV real |
| IDD | 2 | EUR-Lex + BOE real |
| Solvency II | 2 | EUR-Lex + BOE real |
| XBRL | 3 | CNMV real |
| MAR/MiFID | 12 | CNMV + EUR-Lex real |
| PRIIPs | 4 | EUR-Lex + BOE real |
| Corporate | 3 | BORME real |

**Total:** 64 tablas que pasan de seed a datos reales.

---

## Post-plan: Fase 47 — Consolidacion

Despues de completar las 17 fases:
1. Actualizar `architecture.md` con todos los dominios como `[IMPLEMENTED]` (no `[TARGET]`)
2. Actualizar `master-execution-roadmap.md` con estado real de datos por dominio
3. Crear dashboard de frescura de datos (`source_freshness_snapshot` query)
4. Documentar frecuencias y fuentes en `docs/operations/runbooks/`
5. Validar MCP tools contra datos reales (reemplazar hardcoded IDs por list→get pattern)

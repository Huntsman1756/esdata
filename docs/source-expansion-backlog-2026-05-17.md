# Source Expansion Backlog - 2026-05-17

## Contract

This file tracks source families requested on 2026-05-17. It is not a claim that all rows are loaded. Status values:

- `implemented_loaded`: code and production rows exist.
- `implemented_partial`: code and some production rows exist, but coverage is partial.
- `ready_for_ingestion`: code supports the source; production rows still need a worker run.
- `target`: source identified, implementation pending.
- `do_not_mix`: related to an existing domain, but must remain a separate family/table.

## Current Snapshot

| Domain | Status | Notes |
| --- | --- | --- |
| AEAT modelos | `implemented_partial` | 219 modelos, 31k+ casillas; 187/193/198/216/290/296 with structured instructions/keys complete, 200/303 partial. |
| AEAT CDI | `target` | Official sources identified; must be separate double-tax-treaty family, not generic AEAT docs. |
| AEAT GI42 / CRS Modelo 289 | `target` | Procedure source identified; useful for CRS/FATCA workflow expansion. |
| BOE consolidated legislation | `ready_for_ingestion` | Core tax laws loaded; repo now also supports RD 813/2023 (`RD_813_2023`). Production rows need worker run after deploy. |
| BOE diario | `implemented_partial` | Daily non-consolidated notices go to `documento_interpretativo` with `tipo_fuente='boe_diario'`; not automatically committed to repo, loaded by cron/DB. |
| CNMV | `ready_for_ingestion` | Circulares, guias tecnicas and documentos a consulta are separated; repo now adds ESI normativa/modelos families as dedicated CNMV document types. Production rows need worker run after deploy. |
| EUR-Lex | `implemented_partial` | Curated CELEX seed exists, including EMIR `32012R0648`; full ISRB/Q&A coverage is pending. |
| ESMA markets | `ready_for_ingestion` | MiFIR/MiCA/DLT and selected reporting schemas/rules loaded; repo now includes MiFIR reporting hub, ISRB Article 26 and Q&A index as reporting documents. Production rows need worker run after deploy. |
| Banco de Espana | `implemented_partial` | Small current corpus loaded; circulars and financial-system regulation index need expansion. |
| BORME | `implemented_partial` | Pilot rows loaded; improvement should focus on structured company events and freshness. |
| DGT | `implemented_loaded` | 18,631 consultas vinculantes loaded at last production snapshot; completeness still depends on source discovery limits. |
| TEAC | `implemented_partial` | 10 resoluciones loaded; DYCTEA and doctrina historica need broader ingestion. |
| AEPD | `implemented_partial` | 25 docs loaded; circulars/normativa/instrucciones/transparency families need separation. |
| SEPBLAC | `ready_for_ingestion` | 2 docs loaded; repo now discovers official normativa nacional/comunitaria and obligaciones pages by default. Production rows need worker run after deploy. |
| Sanctions / screening | `ready_for_ingestion` | OFAC entries exist; repo now adds an official EU sanctions XML parser and cron service. EU production rows depend on a reachable/configured Commission FSF XML export URL. UN/SEPBLAC sanctions remain target. |
| GIIN / FATCA IRS | `implemented_partial` | GIIN registry and Modelo 290/FATCA rules exist; IRS FATCA source family needs explicit contract. |
| PGC / ESEF | `implemented_partial` | PGC data and XBRL tables exist; ESMA ESEF taxonomy element/label/mapping tables remain target. |

## BOE / EUR-Lex Financial Core

| Item | Official reference | Code status | Contract |
| --- | --- | --- | --- |
| LIVMC | `BOE-A-2023-7053` | `implemented_partial`, 356 production rows | Spanish securities-market law, primary obligation source. User-provided `BOE-A-2023-13494` is not LIVMC. |
| LPBC-FT | `BOE-A-2010-6737` | `implemented_partial`, 80 production rows as `LEY10_2010` | Keep canonical code `LEY10_2010`; aliases `LPBC`, `LPBCFT`, `PBCFT` point to it. Caveat: 2 BOE blocks skipped due invalid upstream date payload. |
| RD 1082/2012 | `BOE-A-2012-9716` | `implemented_partial`, 167 production rows | Spanish IIC regulation, primary/subordinate regulatory source. |
| RD 813/2023 | `BOE-A-2023-22763` | `ready_for_ingestion` as `RD_813_2023` | Regime for investment firms/ESI, primary/subordinate Spanish source for sociedad de valores back-office. |
| EMIR | `CELEX:32012R0648` | `implemented_partial`, 137 production rows in `eurlex_market` | EU regulation via EUR-Lex, not BOE. Common `norma/articulo` seed is metadata-only; official articles are exposed via `/v1/eurlex/market/32012R0648`. |

## Target Source Families

### AEAT / Hacienda

- CDI AEAT official page: `https://sede.agenciatributaria.gob.es/Sede/normativa-criterios-interpretativos/fiscalidad-internacional/convenios-doble-imposicion-firmados-espana.html`
- Hacienda CDI alpha page: `https://www.hacienda.gob.es/es-ES/Normativa%20y%20doctrina/Normativa/CDI/Paginas/CDI_Alfa.aspx`
- CRS Modelo 289 procedure: `https://sede.agenciatributaria.gob.es/Sede/procedimientoini/GI42.shtml`
- Helper repositories to evaluate only as tooling references, not authoritative corpus: `babu-cat/AEAT`, `OpenHacienda/puntoBOE`.

### CNMV

- Normativa comunitaria.
- Circulares CNMV.
- Legislacion CNMV / ESI (`normativa_esi_cnmv`, ready for ingestion).
- Guias tecnicas.
- FAQ normas/recomendaciones.
- Modelos normalizados ESI (`modelo_esi_cnmv`, ready for ingestion) and IM (target).
- Libro jurisprudencia, arboles 1 and 2.

Each must keep a separate `tipo_documento`/contract. Registers and forms should become structured tables where possible, not generic documents.

### ESMA / EUR-Lex

- ESMA MiFIR reporting page and documents (`ready_for_ingestion`: reporting hub, transaction reporting schema/instructions/validation rules, ISRB Article 26 and Q&A index).
- ESMA CSDR reporting.
- ESMA SFTR reporting.
- ESMA Interactive Single Rulebook.
- ESMA Q&A.
- ISRB acts: MiFIR, EMIR, SFTR, SECR, Benchmarks, CRAR, MiCA, Prospectus, MiFID II, UCITS, Transparency Directive, DORA, SSR, CSDR.
- `Ansvar-Systems/EU_compliance_MCP` can be reviewed as implementation inspiration only; official EUR-Lex/ESMA remain source of truth.

### Banco de Espana

- Circulars chronological index.
- Financial-system regulation page.
- BOE financial code page.

### TEAC / AEPD / SEPBLAC

- TEAC DYCTEA and doctrina historica.
- AEPD circulars, normativa, instrucciones, and data-protection transparency information.
- SEPBLAC national and EU normativa plus obligations pages (`ready_for_ingestion`).

### Screening / Sanctions

- EU sanctions parser/cron is `ready_for_ingestion`; production rows require a reachable/configured official Commission FSF XML export URL.
- UN and SEPBLAC sanctions remain pending.
- OpenOwnership, FollowTheMoney, Memorious, Nomenklatura, OpenSanctions and Yente are tooling/data-model candidates, not official legal sources by themselves.

### PGC / ESEF

- ESMA ESEF taxonomy 2024 ZIP.
- ICAC taxonomia contable.
- CNMV taxonomy report.
- Proposed target tables: `esef_taxonomy_element`, `esef_label`, `esef_mapping_pgc`.

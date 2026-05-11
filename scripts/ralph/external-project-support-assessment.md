# Ralph External Project Support Assessment

Date: 2026-05-10
Scope: candidate open-source projects supplied by the user, evaluated as helpers for empty-table remediation and MCP hardening.

## Rule

These projects are not ground truth for Spanish tax/legal answers unless they are themselves official institutional sources. They may be used for:

- parsers,
- schemas,
- normalization,
- connector patterns,
- validation logic,
- MCP architecture patterns,
- privacy/security controls.

They must not be used to silently populate tax/legal facts unless the persisted record points back to an official source such as AEAT, BOE, EUR-Lex, ESMA, CNMV, Banco de España, AEPD, DGT, or another allowed institutional source.

## Highest-Value Candidates

### 1. Arelle / XBRL

Project: `Arelle/Arelle`

Evidence: Arelle describes itself as an end-to-end open-source XBRL platform with CLI, web service, and Python API, supporting XBRL, dimensions, inline XBRL, xBRL-JSON/xBRL-CSV, and validation.

Use here: HIGH.

Target empty tables:

- `xbrl_company`
- `xbrl_filing`
- `xbrl_fact`

Safe integration:

- Use Arelle only as the parser/validator for official CNMV/ESEF/iXBRL filings.
- Persist source URL, filing identifier, checksum, ingestion timestamp, validation result, and parser version.

Unsafe integration:

- Loading sample XBRL or SEC-style examples to satisfy local row counts.

Decision: prioritize after identifying official CNMV/ESEF filing source.

### 2. ESMA Data Py

Project: `European-Securities-Markets-Authority/esma_data_py`

Evidence: package provides tools to search and download data from the ESMA register/publication tool.

Use here: HIGH.

Target empty tables:

- `emir_clearing_member`
- `emir_trade_report` only if official aggregate/reporting data exists, not synthetic trades
- `mifid_*` reference/registry tables where ESMA publishes register data
- `aifmd_fund`, `ucits_fund`, where ESMA/CNMV register mapping is official
- possible `casp`, `tokenized_asset`, `wallet_custodian` if ESMA register endpoints cover the target records

Safe integration:

- Treat ESMA as official EU source.
- Add source family `esma`.
- Store ESMA download link, publication date, file hash, and register name.

Decision: high-priority candidate for market-regulatory empty tables.

### 3. PyGLEIF

Project: `ggravlingen/pygleif`

Evidence: Python library queries the GLEIF API and supports fetching a specific LEI and searching for LEI by organisation number.

Use here: HIGH.

Target empty tables:

- `entity_identifiers`
- `entity_aliases`
- `beneficial_owner_record` only for identity enrichment, not ownership assertion
- `pbc_entity`
- `transparency_issuer`
- `crd_brrd_emir_entity`

Safe integration:

- Use GLEIF as an official/entity identity source for LEI identifiers and legal names.
- Store GLEIF API URL, LEI, entity name, registration status, and retrieval timestamp.

Unsafe integration:

- Inferring ownership/control from LEI data alone.

Decision: high-priority for identity/LEI remediation.

### 4. OpenSanctions / Yente / Nomenklatura / FollowTheMoney

Projects:

- `opensanctions/opensanctions`
- `opensanctions/yente`
- `opensanctions/nomenklatura`
- `alephdata/followthemoney`

Evidence:

- OpenSanctions is an open database of sanctions, persons of interest, and PEPs.
- Yente provides entity search and bulk matching API.
- Nomenklatura integrates FollowTheMoney streams from multiple sources.
- FollowTheMoney is an entity data model and processing toolkit.

Use here: MEDIUM-HIGH.

Target empty tables:

- `screening_entries`
- `screening_matches`
- `pbc_entity`
- `beneficial_owner_record`
- `ubo_record`
- `ownership_relation`
- `ownership_share`

Safe integration:

- Use data model and matching patterns.
- Use OpenSanctions only if license/commercial restrictions are acceptable and each dataset source is allowed.
- For Spanish compliance, prefer official EU sanctions lists, UN, OFAC if allowed, SEPBLAC/CNMV/BDE official lists where available.

Unsafe integration:

- Treating OpenSanctions as the sole authoritative source for Spanish legal obligations.
- Persisting commercial-restricted data without license review.

Decision: useful for matching architecture; official-list ingestion should still be direct where possible.

### 5. OpenOwnership BODS

Project: `openownership/data-standard`

Evidence: Beneficial Ownership Data Standard provides a specification for modelling and publishing beneficial ownership and control information.

Use here: HIGH for schema design, not data source.

Target empty tables:

- `beneficial_owner_record`
- `ubo_record`
- `ownership_relation`
- `ownership_share`

Safe integration:

- Map local ownership tables to BODS concepts.
- Use BODS validation for imported ownership data.

Unsafe integration:

- Generating ownership records without official/company-provided verified evidence.

Decision: high-priority schema/control reference.

### 6. MCP-BOE / Spanish Law MCP / AEAT MCP / Datos Gob MCP

Projects:

- `ComputingVictor/MCP-BOE`
- `Ansvar-Systems/spanish-law-mcp`
- `iMark21/aeat-mcp`
- `AlbertoUAH/datos-gob-es-mcp`

Evidence:

- MCP-BOE connects directly to the official BOE API for consolidated legislation, daily summaries, BORME, auxiliary tables, PDF extraction, and LLM-friendly tools.
- Spanish Law MCP claims a BOE/EUR-Lex sourced database with daily updates, provision search, EU cross-references, and hosted HTTP MCP.
- AEAT MCP states all information comes exclusively from official AEAT/BOE sources and exposes fiscal tools.
- datos-gob-es-mcp shows useful MCP architecture: tools, resources, prompts, async HTTP, rate limiting, cache, and API integrations.

Use here: HIGH for MCP design and test patterns; LOW as data source.

Target gaps:

- Tool naming/boundary clarity.
- Resources and prompt templates.
- BOE daily/BORME watcher design.
- Golden test cases for AEAT/BOE exact citations.

Safe integration:

- Borrow design patterns, not data.
- Add comparative tests: exact BOE id, article lookup, daily BOE/BORME summary, fiscal tool provenance.

Unsafe integration:

- Copying their datasets as ground truth without official-source provenance in our DB.

Decision: use for benchmarking and MCP ergonomics.

## Medium-Value Candidates

### Legal Reference Extraction / OLDP / Legalize ES / Your AI Lawyer

Projects:

- `openlegaldata/legal-reference-extraction`
- `openlegaldata/oldp`
- `legalize-dev/legalize-es`
- `arnabdeypolimi/your-ai-lawyer`

Use here: MEDIUM.

Target areas:

- `obligacion_documento`
- `obligacion_micro_obligacion`
- legal citation extraction and normalization
- retrieval quality tests

Notes:

- `legal-reference-extraction` is German-law oriented, but useful as architecture for citation spans and raw/canonical text mapping.
- `OLDP` is a legal document/search platform pattern.
- `legalize-es` may be useful as a comparison corpus, but official BOE remains the source of truth.
- `your-ai-lawyer` is useful as citation-oriented knowledge-base architecture, not as Spanish tax data authority.

Decision: useful for citation extraction architecture, not immediate table population.

### Memorious / OpenAleph

Projects:

- `alephdata/memorious`
- `openaleph/openaleph`

Use here: MEDIUM.

Target areas:

- official-source crawling framework,
- document collection pipelines,
- investigation/search UX patterns.

Decision: useful if current workers become too ad hoc; not needed for immediate local gate.

### W3C DPV / IAB TCF / DataBunker / Anonimatron

Projects:

- `w3c/dpv`
- `InteractiveAdvertisingBureau/GDPR-Transparency-and-Consent-Framework`
- `securitybunker/databunker`
- `realrolfje/anonimatron`

Use here: MEDIUM for privacy/security, LOW for tax/legal data population.

Target areas:

- privacy vocabulary,
- consent/purpose taxonomy,
- PII vault/tokenization ideas,
- safe test data anonymization.

Decision:

- DPV is a good ontology reference for data-processing purpose metadata.
- DataBunker is useful as architecture inspiration for PII vaulting.
- Anonimatron can help create non-production test data, but must not be used to populate official compliance tables.
- IAB TCF is adtech-specific; only relevant if consent-management metadata enters scope.

### Currency / Calendar

Projects:

- `alexprengere/currencyconverter`
- `RubyMoney/eu_central_bank`
- `commenthol/date-holidays`

Use here: MEDIUM.

Target areas:

- ECB rates for broker/tax calculations,
- holiday calendars for date calculations.

Important caveat:

- `currencyconverter` embeds ECB data by default and warns it may not be up to date; for compliance use, fetch the current ECB file and store source metadata.
- Date holiday libraries are not AEAT fiscal-deadline sources. They can support business-day adjustment only after AEAT deadline source exists.

Decision: useful helper libraries; not official fiscal calendar source.

### AEAT / Spanish Tax Tools

Projects:

- `gisce/sii`
- `OpenHacienda/puntoBOE`
- `paumrch/larenta`
- `GeiserX/DeclaRenta`
- `vaijira/burocratin`
- `fawno/AEAT`
- `NeoRazorX/facturascripts`
- `OCA/l10n-spain`

Use here: LOW-MEDIUM.

Safe uses:

- AEAT file format parsing/validation ideas.
- NIF/SOAP integration patterns.
- Modelo 720/100/721 workflow examples.
- Spanish accounting/localization concepts.

Unsafe uses:

- Importing tax facts, rates, deadlines, or deductions from community repos as authoritative data.
- AGPL/GPL code reuse without license review.

Decision: benchmark and parser ideas only unless a specific official AEAT/BOE-backed artifact is extracted and validated.

## PSD2 / Open Banking

Projects:

- `adorsys/xs2a`
- `adorsys/open-banking-gateway`

Evidence:

- `xs2a` is a reference Java implementation of Berlin Group NextGenPSD2 XS2A, with consent management and ASPSP profile modules.
- `open-banking-gateway` provides REST APIs, tools, adapters, and connectors for open banking APIs.

Use here: MEDIUM.

Target empty tables:

- `psd2_consent`
- `psd2_incident_report`
- selected PSD2/API/consent schema design

Safe integration:

- Use as schema/API workflow inspiration.
- Use official EBA/BDE/ESMA registries for actual regulated entities and statuses.

Unsafe integration:

- Treating test banks, model banks, or connector demo data as production compliance records.

Decision: useful for API/consent modeling, not for authoritative Spanish PSD2 data.

## Recommended Ralph Backlog

### EXT-001: XBRL Official Filing Ingestion

Use Arelle for parsing and validation.

Acceptance:

- Identify official CNMV/ESEF source.
- Ingest one real filing.
- Populate `xbrl_company`, `xbrl_filing`, `xbrl_fact` with source URL/hash/timestamp.
- No sample filings accepted.

### EXT-002: GLEIF Entity Identity

Use PyGLEIF or direct GLEIF API.

Acceptance:

- Populate `entity_identifiers` and `entity_aliases` for entities already present from official sources.
- Store GLEIF source URL, LEI, registration status, retrieval timestamp.
- No ownership inference from LEI alone.

### EXT-003: ESMA Register Ingestion

Use ESMA official package/API where appropriate.

Acceptance:

- Download at least one official ESMA register file.
- Populate a narrowly selected target table with provenance and hash.
- Add source family `esma`.

### EXT-004: Ownership Schema Alignment

Use OpenOwnership BODS as schema/reference.

Acceptance:

- Map local ownership tables to BODS concepts.
- Add validation tests.
- Do not populate without official or user-verified source records.

### EXT-005: Screening Architecture

Use OpenSanctions/Yente/Nomenklatura/FollowTheMoney patterns.

Acceptance:

- Decide license/commercial constraints.
- Prefer direct official list ingestion for persisted `screening_entries`.
- Implement matching tests with synthetic test entities only, not production entries.

### EXT-006: MCP Benchmark Suite

Use MCP-BOE, AEAT MCP, Spanish Law MCP, and datos-gob-es-mcp for tool ergonomics and test coverage.

Acceptance:

- Add benchmark cases for exact BOE id, article lookup, daily BOE/BORME search, source freshness, and traceability.
- Fail on missing source URL, missing BOE reference, stale silent answer, or ambiguous tool result.

## Not Recommended For Direct Integration Now

- `RubyMoney/eu_central_bank`: Ruby stack mismatch; use Python ECB fetch or direct ECB source instead.
- `facturascripts` / `OCA/l10n-spain`: useful as accounting/localization references, but too broad and license-heavy for current MCP table remediation.
- `larenta`, `DeclaRenta`, `burocratin`: useful UX/parser references for tax workflows, but not authoritative data sources.
- `IAB TCF`: adtech-specific; not directly relevant unless consent-management scope appears.

## Current Decision

Do not add these dependencies blindly.

Next safest implementation order:

1. Arelle for XBRL after official CNMV/ESEF source discovery.
2. PyGLEIF/direct GLEIF for entity identifiers.
3. ESMA official register ingestion for market-regulatory tables.
4. OpenOwnership BODS schema mapping for ownership tables.
5. MCP benchmark expansion from AEAT/BOE/spanish-law examples.


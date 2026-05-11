# ESData Local Table Remediation Registry Draft

Local snapshot: 2026-05-10. Source: local Docker Postgres `pg_stat_user_tables` exact `count(*)` scan.

Rule: an empty table is acceptable only when classified as `allowed_empty` with a concrete operational reason. Compliance/domain tables must be populated from official sources or remain `blocker`. Fixture, demo, sample, or synthetic seeds do not count as real data.

## Gate Rules

- `blocker`: must have official ingestion implemented and verified before VPS deployment.
- `allowed_empty`: may remain empty, but local gate must verify schema, RLS, and insert/write behavior in tests where applicable.
- `derived_blocker`: must be generated from already-ingested official records with traceability.
- `workflow_empty`: real rows only appear after user activity, incidents, reviews, eval runs, or alerts.

## IRNR / AEAT Model Data

| Table | Classification | Action |
|---|---:|---|
| `irnr_instruccion` | blocker | Extend `aeat_irnr.py` to fetch official AEAT instruction pages for models 210/211/213/216/226/228/247/296 and persist sections with `source_url`. |
| `irnr_withholding_rate` | blocker | Ingest official AEAT/BOE IRNR rates with effective dates, legal basis, and uncertainty notes. Reject `seed_irnr_rates.py` as authoritative. |
| `modelo_fiscal_calendar` | workflow_empty | Deadline table; keep empty until current AEAT fiscal calendar ingestion is implemented. Do not infer deadlines from model pages. |
| `modelo_formato` | populated | Official AEAT design-record reference populated from `modelo_campana.url_formato` by `official_regulatory_references.py`; field-level parsing still requires official design document extraction. |

## BOE / Document Decomposition / Lineage

| Table | Classification | Action |
|---|---:|---|
| `documento_fragmento` | derived_blocker | Split existing official `documento_interpretativo` rows into retrievable fragments with source document linkage. |
| `documento_seccion` | derived_blocker | Extract sections from official documents, preserving `documento_interpretativo.id` and source URL. |
| `documento_cnmv_version` | blocker | Populate from official CNMV version metadata where available; otherwise classify unavailable per document. |
| `data_lineage` | derived_blocker | Link derived rows to source records and sync_log runs. |
| `entity_aliases` | workflow_empty | Derived official alias table; `entity_identity.py --run-once` found no GLEIF aliases locally, so no fake aliases. |
| `entity_identifiers` | workflow_empty | Derived official identifier table; `entity_identity.py --run-once` found no GLEIF LEIs locally, so no fake identifiers. |

## PGC / Accounting / XBRL Mapping

| Table | Classification | Action |
|---|---:|---|
| `pgc_marco` | blocker | Populate from official BOE PGC legal text. |
| `pgc_norma_valoracion` | blocker | Populate valuation rules from official BOE PGC legal text. |
| `pgc_cuenta` | blocker | Populate chart of accounts from official BOE PGC source; reject corrupted/static seed as authoritative. |
| `pgc_estado_financiero` | blocker | Populate official financial statement structures from BOE PGC source. |
| `pgc_cuenta_fiscal_ref` | workflow_empty | Human-reviewed derived mapping table. Keep empty until official or reviewed mappings exist; do not infer automatically. |
| `pgc_cuenta_modelo_aeat_ref` | workflow_empty | Human-reviewed PGC-to-AEAT mapping table. Keep empty until official or reviewed mappings exist; do not infer automatically. |
| `pgc_xbrl_mapping` | derived_blocker | Populate from official taxonomy mapping or human-reviewed derived mapping with evidence. |
| `xbrl_taxonomy` | blocker | Populate from official ESEF/ESMA or IFRS taxonomy sources. |
| `xbrl_company` | workflow_empty | Filing-derived issuer table. Keep empty until an official CNMV/ESEF filing ingestion target is configured. |
| `xbrl_filing` | workflow_empty | Filing ingestion table. Keep empty until official CNMV/ESEF filings are configured; fixture-first tests do not count. |
| `xbrl_fact` | workflow_empty | Filing-derived fact table. Keep empty until official XBRL/iXBRL filings are configured; fixture-first tests do not count. |

## International Tax / IRS / DTA

| Table | Classification | Action |
|---|---:|---|
| `irs_fiscal_norma` | populated | Official IRS reference metadata populated from IRS publications/instructions by `official_regulatory_references.py`. |
| `irs_modelo` | populated | Official IRS W-8 model metadata populated from IRS form pages by `official_regulatory_references.py`. |
| `irs_tin_reference` | populated | Minimal official IRS/OECD TIN references populated by `official_regulatory_references.py`; no example TINs fabricated. |
| `irs_w8_form` | populated | Official W-8 form reference metadata populated by `official_regulatory_references.py`. |
| `irs_withholding_rule` | populated | Minimal official IRS Publication 515 default withholding reference populated by `official_regulatory_references.py`; treaty analysis remains explicit. |
| `giin_registry` | workflow_empty | IRS FATCA FFI/GIIN official monthly CSV ZIP ingestion. No seed fallback is allowed; keep unavailable until official IRS download succeeds. |

## DAC / Crypto / MiCA

| Table | Classification | Action |
|---|---:|---|
| `crypto_asset` | workflow_empty | Asset-specific MiCA/user workflow table; keep empty until official ESMA/EBA/CNMV registry ingestion is configured. |
| `crypto_transaction` | workflow_empty | Real rows are user/workflow data; local gate should not require production rows. |
| `dac_reporting_entity` | workflow_empty | Reporting-entity workflow table; keep empty until real DAC onboarding or official registry ingestion exists. |
| `dac_crypto_report` | workflow_empty | User/reporting workflow table; no fake reports. |
| `dac_wallet_holder` | workflow_empty | User/reporting workflow table; no fake holders. |
| `casp` | workflow_empty | Entity registry table; keep empty until official MiCA/CASP register ingestion is configured. |
| `tokenized_asset` | workflow_empty | Asset-specific table; keep empty until official registry/source ingestion exists. |
| `wallet_custodian` | workflow_empty | Custodian registry table; keep empty until official CASP/custodian source ingestion exists. |

## CSRD / Sustainability / SFDR

| Table | Classification | Action |
|---|---:|---|
| `csrd_company` | workflow_empty | Company/reporting workflow table; keep empty until official ESAP/CNMV filing ingestion exists. |
| `csrd_entity_report` | workflow_empty | Filing-derived table; keep empty until official CSRD report ingestion exists. |
| `csrd_esg_data_point` | workflow_empty | Derived filing table; keep empty until official CSRD reports are ingested with lineage. |
| `csrd_ess` | populated | Official ESRS reference catalog populated from EUR-Lex Delegated Regulation (EU) 2023/2772 by `official_regulatory_references.py`. |
| `csrd_double_materiality` | workflow_empty | User analysis output; no synthetic rows. |
| `sfdr_product` | workflow_empty | Product/disclosure table; keep empty until official manager/product disclosure ingestion exists. |
| `sfdr_fund` | workflow_empty | Fund-specific table; keep empty until official fund/product source ingestion exists. |
| `sfdr_entity_paci` | workflow_empty | Entity disclosure table; keep empty until official SFDR PAI disclosures are ingested. |
| `sfdr_paci_indicator` | workflow_empty | Product disclosure-derived table; keep empty until official SFDR disclosures are ingested. |
| `sfdr_pre_contractual` | workflow_empty | Official disclosure document table; keep empty until source URLs are ingested. |
| `sfdr_annual_report` | workflow_empty | Official periodic disclosure table; keep empty until source URLs are ingested. |

## AIFMD / UCITS / PRIIPs / Solvency

| Table | Classification | Action |
|---|---:|---|
| `aifmd_fund` | workflow_empty | Fund registry table; keep empty until official CNMV/ESMA fund ingestion is configured. |
| `aifmd_liquidity_management` | workflow_empty | Fund-specific metadata; keep empty until official filings or supervised workflow data exist. |
| `aifmd_regulatory_report` | workflow_empty | Filing table; keep empty until official report ingestion is configured. |
| `ucits_fund` | workflow_empty | Fund registry table; keep empty until official CNMV/ESMA UCITS ingestion is configured. |
| `ucits_regulatory_report` | workflow_empty | Filing table; keep empty until official UCITS report ingestion is configured. |
| `priips_product` | workflow_empty | Product-specific table; keep empty until official PRIIPs/KID source ingestion exists. |
| `priips_kid` | workflow_empty | KID document table; keep empty until official KID URLs are ingested. |
| `solvency_ii_entity` | workflow_empty | Entity-specific insurance table; keep empty until official DGSFP/EIOPA ingestion is configured. |
| `solvency_ii_sfp` | workflow_empty | Public report table; keep empty until official Solvency II report ingestion exists. |

## CRD / BRRD / EMIR

| Table | Classification | Action |
|---|---:|---|
| `crd_brrd_emir_entity` | workflow_empty | Regulated-entity table; keep empty until BDE/CNMV/EBA/ESMA registry ingestion is configured. |
| `crd_capital_position` | workflow_empty | Disclosure-derived table; keep empty until official disclosures are ingested. |
| `crd_stress_test` | workflow_empty | Stress-test result table; keep empty until official EBA source ingestion exists. |
| `brrd_bail_in` | workflow_empty | Resolution/bail-in event table; keep empty until official event/source ingestion exists. |
| `emir_trade_report` | workflow_empty | Reporting workflow table; no synthetic trades. |
| `emir_clearing_member` | workflow_empty | Clearing-member registry table; keep empty until official ESMA/CCP source ingestion is configured. |

## DORA / ICT Risk

| Table | Classification | Action |
|---|---:|---|
| `dora_ict_risk_register` | workflow_empty | Entity-specific internal register; can be empty locally. |
| `dora_incident_classification_framework` | populated | Official DORA RTS reference populated from EUR-Lex Delegated Regulations (EU) 2024/1772 and 2025/301 by `official_regulatory_references.py`. |
| `dora_penetration_test` | workflow_empty | Entity-specific testing record; no fake tests. |
| `dora_third_party_provider` | workflow_empty | Entity-specific vendor register unless official oversight registry is used. |
| `dora_tic_incident` | workflow_empty | Incident table; healthy local state may be zero. |

## MiFID / MAR / IDD / LIVMC / Transparency

| Table | Classification | Action |
|---|---:|---|
| `mifid_best_execution_record` | workflow_empty | Entity-specific compliance record. |
| `mifid_client_category` | workflow_empty | Client classification workflow table; no fake client rows. |
| `mifid_compensation_policy` | workflow_empty | Entity-specific policy table. |
| `mifid_conflict_of_interest_registry` | workflow_empty | Entity-specific register. |
| `mifid_insider_list` | workflow_empty | Entity-specific list. |
| `mifid_order_record` | workflow_empty | Entity-specific order/audit record. |
| `mifid_product_governance` | workflow_empty | Entity/product-specific governance record. |
| `mifid_suitability_report` | workflow_empty | Entity/client-specific report. |
| `mar_insider_communication` | workflow_empty | Entity-specific communication record. |
| `mar_insider_transaction` | workflow_empty | Entity-specific transaction record. |
| `mar_market_manipulation_indicator` | workflow_empty | Surveillance configuration/output table; no official instrument-specific indicators are configured locally. |
| `mar_suspicious_transaction_report` | workflow_empty | Incident/reporting workflow table. |
| `idd_distributor` | workflow_empty | Distributor registry table; keep empty until official DGSFP/CNMV source ingestion is configured. |
| `idd_product_uci` | workflow_empty | Entity/product-specific table unless official registry source is configured. |
| `livmc_client_protection` | workflow_empty | Client-protection workflow table; keep empty until real supervised entity/client records exist. |
| `livmc_voice_procedure` | workflow_empty | Entity procedure table; keep empty until real entity policy workflow records exist. |
| `transparency_internal_rule` | workflow_empty | Entity-specific internal rule. |
| `transparency_issuer` | workflow_empty | Issuer registry table; keep empty until official CNMV issuer ingestion is configured. |
| `transparency_regulated_information` | workflow_empty | Filing table; keep empty until official CNMV regulated-information ingestion exists. |
| `transparency_voting_rights` | workflow_empty | Significant holding/voting-rights table; keep empty until official CNMV source ingestion exists. |

## PSD2 / SEPA / Consumer Credit

| Table | Classification | Action |
|---|---:|---|
| `psd2_consent` | workflow_empty | User/entity workflow table. |
| `psd2_incident_report` | workflow_empty | Incident workflow table. |
| `sepa_payment_rule` | populated | Official EPC SEPA rulebook reference rows populated by `official_regulatory_references.py`. |
| `consumer_credit_contract` | workflow_empty | Entity/customer workflow table. |
| `consumer_credit_disclosure` | workflow_empty | Contract/disclosure workflow table; keep empty until real consumer-credit documents are ingested. |
| `consumer_credit_overindebtedness` | workflow_empty | Borrower/procedure workflow table; no fake borrower rows. |

## Ownership / UBO / PBC / Fraud / Screening

| Table | Classification | Action |
|---|---:|---|
| `beneficial_owner_record` | workflow_empty | Beneficial-owner workflow/source table; keep empty until official register/BORME/user-verified source exists. |
| `ownership_relation` | workflow_empty | Derived ownership table; keep empty until official BORME/registry records support a relation with lineage. |
| `ownership_share` | workflow_empty | Derived ownership table; keep empty until official BORME/registry records support a share with lineage. |
| `ubo_record` | workflow_empty | UBO source table; keep empty until official/user-verified UBO records exist. |
| `pbc_entity` | workflow_empty | Entity-specific prudential/AML table; keep empty until official supervised-entity source ingestion exists. |
| `pbc_internal_control` | workflow_empty | Entity-specific internal control table. |
| `pbc_obligated_subject` | populated | Official Ley 10/2010 article 2 subject-category metadata populated from BOE by `official_regulatory_references.py`. |
| `fraud_incident` | workflow_empty | Incident table. |
| `fraud_prevention_program` | workflow_empty | Entity-specific program table. |
| `fraud_risk_assessment` | workflow_empty | Entity-specific assessment table. |
| `screening_lists` | populated | Official EU/SEPBLAC list metadata populated by `official_regulatory_references.py`; entries require a separate official-list parser. |
| `screening_entries` | workflow_empty | Official list-entry table; keep empty until a parser for official EU/SEPBLAC/other allowed lists is implemented. |
| `screening_matches` | workflow_empty | Match output table; can be empty until screening runs. |
| `suspicious_activity_report` | workflow_empty | Reporting workflow table. |

## Obligations / Controls

| Table | Classification | Action |
|---|---:|---|
| `obligacion_regulatoria` | populated | Official AEAT model-reference obligations populated by `official_regulatory_references.py` with partial-reference metadata; no deadlines inferred. |
| `obligacion_documento` | workflow_empty | Link table; keep empty until obligations are linked to exact official source documents with reviewed relation type. |
| `obligacion_micro_obligacion` | workflow_empty | Derived mapping; keep empty until official obligations are decomposed and reviewed. |
| `obligacion_internacional` | workflow_empty | International obligation table; keep empty until official CRS/FATCA/DAC obligation ingestion is implemented. |
| `prueba_control` | workflow_empty | Entity-specific control evidence; no fake rows. |

## Operational / AI / Evaluation / Review Tables

| Table | Classification | Action |
|---|---:|---|
| `ai_model_registry` | allowed_empty | Runtime/model configuration table; can be empty locally if no AI model registry is used. Gate verifies schema/RLS. |
| `data_freshness_alerts` | allowed_empty | Alert table; empty is healthy if no SLA breach. Gate verifies alert generation tests. |
| `embedding_version` | allowed_empty | Can be empty until embedding pipeline enabled. Gate must verify retrieval handles absence safely. |
| `eval_run` | workflow_empty | Evaluation run table; only populated after eval execution. |
| `eval_query` | workflow_empty | Evaluation query table; populate via eval suite only, not fake production rows. |
| `human_review` | workflow_empty | Human-review workflow table; zero is acceptable locally. |
| `nota_editorial_interna` | workflow_empty | Internal editorial table; no fake notes. |

# Worker DB retry coverage

Status: IMPLEMENTED as of 2026-05-11.

Scope: `apps/workers/*.py` files that create SQLAlchemy engines with `create_engine(...)`.
Requirement: every in-scope worker must call `ensure_database_connection(engine)` before DB work so Docker DNS/network churn fails loudly and retries before sync logic starts.

In-scope DB worker files: 68
Missing retry guard: 0

## Canonical external identifiers

Workers that persist entities with stable official identifiers must treat the official identifier as immutable identity and must not let a later run overwrite a canonical local `codigo` with an older alias.

Pattern:

- Resolve existing rows first by the official external identifier (`boe_id`, CELEX, official reference, or equivalent).
- If a row exists, update only mutable metadata such as title, URL, coverage/status, timestamps, counters, or hashes.
- Preserve the canonical `codigo` already stored in the database.
- Only insert a new row when no row exists for the official external identifier.

Example from A-04b: `worker-eurlex` may encounter legacy `codigo='MIFID2_2014_65'` for `boe_id='EUR-CELEX-32014L0065'`, but the canonical row must remain `codigo='32014L0065'`.

| Worker file | create_engine calls | Retry guard |
| --- | ---: | --- |
| `aeat_current_designs.py` | 1 | PASS |
| `aeat_irnr.py` | 1 | PASS |
| `aeat_models.py` | 1 | PASS |
| `aepd.py` | 1 | PASS |
| `aifmd_ucits.py` | 1 | PASS |
| `bde.py` | 1 | PASS |
| `bdns.py` | 1 | PASS |
| `boe.py` | 1 | PASS |
| `boe_diario.py` | 1 | PASS |
| `boe_modelos_worker.py` | 2 | PASS |
| `borme.py` | 1 | PASS |
| `cdi.py` | 2 | PASS |
| `cendoj.py` | 1 | PASS |
| `cnmv.py` | 1 | PASS |
| `consumer_credit.py` | 2 | PASS |
| `consumer_credit_real.py` | 1 | PASS |
| `corporate_sustainability.py` | 1 | PASS |
| `crd_brrd_emir.py` | 1 | PASS |
| `csdr.py` | 1 | PASS |
| `csr.py` | 1 | PASS |
| `dac8.py` | 1 | PASS |
| `dac8_real.py` | 1 | PASS |
| `dac_directives.py` | 1 | PASS |
| `dgt.py` | 1 | PASS |
| `dgt_doctrina.py` | 1 | PASS |
| `document_decomposition.py` | 2 | PASS |
| `dora.py` | 1 | PASS |
| `entity_identity.py` | 2 | PASS |
| `eurlex.py` | 1 | PASS |
| `eurlex_market.py` | 1 | PASS |
| `eu_sanctions.py` | 1 | PASS |
| `fraud.py` | 1 | PASS |
| `giin.py` | 1 | PASS |
| `insurance.py` | 1 | PASS |
| `jurisprudencia.py` | 2 | PASS |
| `legalize_es.py` | 1 | PASS |
| `ley112009_socimi.py` | 1 | PASS |
| `ley13_2023.py` | 1 | PASS |
| `ley222014_lecr.py` | 1 | PASS |
| `mar_mifid.py` | 1 | PASS |
| `mica.py` | 1 | PASS |
| `mifid_mar_dora.py` | 1 | PASS |
| `modelos.py` | 1 | PASS |
| `ofac_sdn.py` | 1 | PASS |
| `official_regulatory_references.py` | 1 | PASS |
| `pbc.py` | 1 | PASS |
| `pgc.py` | 2 | PASS |
| `pgc_boe.py` | 2 | PASS |
| `pgc_real.py` | 1 | PASS |
| `pgc_xbrl_mapping.py` | 2 | PASS |
| `priips_ownership.py` | 1 | PASS |
| `prospectos.py` | 1 | PASS |
| `psd2.py` | 1 | PASS |
| `psd2_eba.py` | 1 | PASS |
| `regulatory_watch.py` | 1 | PASS |
| `rirnr.py` | 1 | PASS |
| `screening.py` | 2 | PASS |
| `screening_real.py` | 1 | PASS |
| `sepblac.py` | 1 | PASS |
| `sfdr.py` | 1 | PASS |
| `solvency.py` | 1 | PASS |
| `sustainable_finance.py` | 1 | PASS |
| `teac.py` | 1 | PASS |
| `worker_esma_dlt.py` | 1 | PASS |
| `worker_esma_firds.py` | 1 | PASS |
| `worker_esma_mifir_reporting.py` | 1 | PASS |
| `xbrl.py` | 2 | PASS |
| `xbrl_taxonomy.py` | 1 | PASS |

Out-of-scope helper/dataset modules without `create_engine(...)`: `__init__.py`, `boe_modelos.py`, `boe_pdf_parser.py`, `change_detection.py`, `dead_letter.py`, `embeddings.py`, `entrypoint.py`, `ley112021.py`, `ley12010.py`, `ley222010.py`, `ley272014.py`, `ley62018.py`, `micro_obligations.py`, `modelos_support.py`, `nrv9.py`, `pgc_dataset.py`, `rd2172008.py`, `trlmv.py`, `vocabulary.py`, `vocabulary_validation.py`.

Verification:

```powershell
python -m pytest scripts/tests/test_worker_db_retry_coverage.py -q --basetemp .pytest-tmp
```

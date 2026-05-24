# MiCA CASP / Emisor Token Audit - 2026-05-24

## Scope

`MCP-DATA-05` audits MiCA obligations for:

- `casp`
- `emisor_token`

The slice separates CASP, ART base and EMT partial obligations.

Out of scope:

- `sociedad_valores_verified_ge_24`.
- `all_profiles_pct_verified_ge_70`.
- Promoting `verified=true` from EUR-Lex norm presence alone.

## RED Evidence

VPS commit before local fix: `f1ca85b`.

`mcp_validation_suite.py --read-only --base-url http://api:8000`:

- `casp_obligations_ge_6`: `value=8`, OK.
- `casp_obligations_all_verified`: `value=0`, minimum `6`, FAIL.
- `emisor_token_obligations_ge_8`: `value=8`, OK.
- `emisor_token_obligations_all_verified`: `value=0`, minimum `8`, FAIL.
- `emisor_token_art_base_obligations_completa`: `value=0`, minimum `3`, FAIL.
- `emisor_token_emt_obligations_parcial`: `value=3`, OK.

`mcp_deep_contract_audit.py --base-url http://api:8000`:

- `casp_total=8`
- `casp_verified=0`
- `casp_normas=['32023R1114']`
- `casp_pbc_count=1`
- `casp_art59_count=1`
- `emisor_token_total=8`
- `emisor_token_verified=0`
- `emisor_token_art_completa_count=0`
- `emisor_token_emt_parcial_count=3`
- `emisor_token_art18_note_count=1`
- `emisor_token_art48_note_count=1`

## Data Inventory

Production has 16 MiCA profile obligations:

- CASP: 8 rows.
- `emisor_token`: 8 rows.

All 16 rows share the same evidence state:

- `norma_codigo='32023R1114'`
- `source_url` points to EUR-Lex.
- `source_hash=NULL`
- `capture_date='2026-05-19'`
- `verified=false`
- `safe_to_answer=false`
- `completeness='parcial'`
- `notas` includes `fail-closed until source_hash and capture_date are loaded`

CASP article coverage is present as rows for MiCA arts. 59, 62, 65, 66, 70,
72, 81 and 94.

`emisor_token` article coverage is present as rows for MiCA arts. 18, 19, 25,
35, 45, 48, 51 and 55.

ART base rows are present for:

- art. 18
- art. 19
- art. 35

EMT rows remain explicitly partial for:

- art. 48
- art. 51
- art. 55

The canonical MiCA `norma` row and CASP delegated/implementing norms exist:

- `32023R1114`
- `32025R0299`
- `32025R0305`
- `32025R0306`

However, none of those norm rows has parsed `articulo` rows or normalized
article `content_hash` in production. Norm presence and EUR-Lex URL therefore
cannot prove article text or exact profile applicability.

## Decision

Do not promote CASP or `emisor_token` obligations to `verified=true`.

Do not mark ART base obligations as `completa`.

The safe contract is:

- `verified=true` is accepted only with normalized primary evidence
  (`source_hash` and `capture_date`).
- `verified=false`, `safe_to_answer=false`, `review_required=true`,
  `source_hash=NULL`, `capture_date` present and `evidence_limited` exposed by
  API is accepted as explicit fail-closed.
- ART base is considered present and fail-closed, not complete.
- EMT remains partial.

## Local Change

`scripts/maintenance/mcp_validation_suite.py` now checks:

- `casp_obligations_verified_or_fail_closed`
- `emisor_token_obligations_verified_or_fail_closed`
- `emisor_token_art_base_obligations_present_3`
- `emisor_token_art_base_obligations_verified_or_fail_closed_3`

`scripts/maintenance/mcp_deep_contract_audit.py` now accepts CASP and
`emisor_token` obligations only when each item is verified with evidence or
explicitly fail-closed. ART base is checked through the same contract instead of
requiring `completeness='completa'`.

## Expected VPS Result

After deployment:

- CASP no longer fails merely because rows are unverified.
- `emisor_token` no longer fails merely because rows are unverified.
- ART base no longer fails merely because it is partial; it must be present and
  verified/fail-closed.
- Remaining semantic failures should be limited to `sociedad_valores` aggregate
  coverage and global profile percentage unless another non-MiCA issue appears.

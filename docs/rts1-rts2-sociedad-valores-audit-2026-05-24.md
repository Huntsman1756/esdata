# RTS1/RTS2 Sociedad Valores Audit - 2026-05-24

## Scope

`MCP-DATA-04` audits RTS1/RTS2 obligations for `sociedad_valores`.

Out of scope:

- CASP obligations.
- `emisor_token` obligations.
- Direct optimization of `all_profiles_pct_verified_ge_70`.
- Promoting `verified=true` from EUR-Lex norm presence alone.

## RED Evidence

VPS commit before local fix: `50176b6`.

`mcp_validation_suite.py --read-only --base-url http://api:8000`:

- `rts1_rts2_obligations_all_verified`: `value=12`, expected `0`.
- `sociedad_valores_verified_ge_24`: `value=4`, minimum `24`.
- `all_profiles_pct_verified_ge_70`: `value=8`.

`mcp_deep_contract_audit.py --base-url http://api:8000`:

- `profile_applicability_contracts` failed with:
  - `empresa_servicios_pago_modelo_303_completa`
  - `sociedad_valores_rts1_evidence_notice_verified`
- `sociedad_valores_rts1_rts2_count=4`.
- RTS1 descriptions:
  - `Publicacion de cotizaciones pre-negociacion (SI renta variable)`
  - `Publicacion post-negociacion de operaciones (RTS 1)`

## Data Inventory

Production has 12 RTS1/RTS2 `obligacion_perfil` rows across:

- `agencia_valores`
- `entidad_credito`
- `sociedad_valores`

`eaf` and `empresa_servicios_pago` have zero RTS1/RTS2 rows, as expected.

For `sociedad_valores`, production has four RTS rows:

- RTS 1 pre-trade, `32017R0587`, art. 8.
- RTS 1 post-trade, `32017R0587`, art. 6.
- RTS 2 pre-trade, `32017R0583`, art. 8.
- RTS 2 post-trade, `32017R0583`, art. 10.

All 12 RTS rows share the same evidence state:

- `source_url` points to EUR-Lex.
- `source_hash=NULL`.
- `capture_date='2026-05-18'`.
- `verified=false`.
- `safe_to_answer=false`.
- `completeness='parcial'`.
- `notas` include `fail-closed until source_hash and capture_date are loaded`.

The `norma` rows exist for `32017R0587` and `32017R0583`, but production has no
parsed `articulo` rows for either norm and no normalized `content_hash` on the
norm rows. Norm presence therefore cannot prove either article text or exact
profile applicability.

## Decision

Do not promote RTS1/RTS2 obligations to `verified=true`.

`verified=true` requires primary evidence proving both:

- the RTS norm/article basis, and
- exact applicability to the profile.

The current state is accepted only as explicit fail-closed:

- `verified=false`
- `safe_to_answer=false`
- `review_required=true`
- `source_url` present and EUR-Lex based
- `source_hash=NULL`
- `capture_date` present
- `completeness='parcial'`
- `evidence_limited` notice exposed by API

## Local Change

`scripts/maintenance/mcp_validation_suite.py` replaces the historical
`rts1_rts2_obligations_all_verified` check with
`rts1_rts2_obligations_verified_or_fail_closed`.

`scripts/maintenance/mcp_deep_contract_audit.py` accepts the RTS1
`sociedad_valores` item only when it is verified with evidence or explicitly
fail-closed.

## Validation

Local:

- `python -m pytest scripts/tests/test_maintenance_agents.py -q` -> expected
  focused contract tests pass before VPS deployment.
- `python -m py_compile scripts\maintenance\mcp_validation_suite.py scripts\maintenance\mcp_deep_contract_audit.py`
  -> expected OK.

VPS after deployment of commit `8a3b5d7`:

- `mcp_validation_suite.py --read-only --base-url http://api:8000`:
  `ok=false`, `checks=132`, `failures=5`.
- `rts1_rts2_obligations_verified_or_fail_closed` passes with `value=0`.
- Remaining validation failures:
  - `sociedad_valores_verified_ge_24`
  - `all_profiles_pct_verified_ge_70`
  - `casp_obligations_all_verified`
  - `emisor_token_obligations_all_verified`
  - `emisor_token_art_base_obligations_completa`
- `mcp_deep_contract_audit.py --base-url http://api:8000`: `ok=false`,
  `checks=12`, `failures=3`.
- `profile_applicability_contracts` no longer contains
  `sociedad_valores_rts1_evidence_notice_verified`; it now only reports
  `empresa_servicios_pago_modelo_303_completa`.

Deployment note:

- First `ops` rebuild failed because of a Docker cache snapshot error
  (`parent snapshot ... does not exist`).
- Rebuilding `ops` with `--no-cache` succeeded.

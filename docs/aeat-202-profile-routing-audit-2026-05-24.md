# AEAT Modelo 202 Profile Routing Audit - 2026-05-24

## Scope

`MCP-DATA-03` audits fiscal applicability and profile routing for
`sociedad_valores`, using Modelo 202 as the concrete fiscal obligation under
test.

Out of scope:

- CASP obligations.
- `emisor_token` obligations.
- Direct optimization of `all_profiles_pct_verified_ge_70`.
- Promoting `verified=true` without normalized primary evidence.

## RED Evidence

VPS commit before local fix: `04745b7`.

`mcp_validation_suite.py --read-only --base-url http://api:8000`:

- `modelo_202_all_profiles_loaded`: `value=0`, `minimum=6`.
- `perfil_sociedad_valores_fiscal_routing_contract`: `ok=false`.
- Routing details: `modelo_202_count=1`, `modelo_202_verified=[false]`.

Production DB has exactly six Modelo 202 profile rows:

- `agencia_valores`
- `eaf`
- `empresa_servicios_pago`
- `entidad_credito`
- `sgiic`
- `sociedad_valores`

All six rows share the same evidence state:

- `modelo_aeat='202'`
- `norma_codigo='LIS'`
- `articulo_referencia='art. 40'`
- `source_url='https://sede.agenciatributaria.gob.es/Sede/impuesto-sobre-sociedades/modelo-202.html'`
- `source_hash=NULL`
- `capture_date='2026-05-17'`
- `verified=false`
- `safe_to_answer=false`
- `completeness='parcial'`
- `notas` includes `fail-closed until source_hash and capture_date are loaded`

The active Modelo 202 API response exposes official resources with hashes for
the current campaign, including:

- AEAT help page.
- Design register XLSX.
- Design register annex XLSX.
- Electronic form.
- Instructions.
- LIS normative page.
- Model page.

However, those active model-level resources are not reconciled into the six
`obligacion_perfil` rows. The persisted profile rows still lack `source_hash`.

## Decision

Do not promote the six Modelo 202 profile obligations to `verified=true`.

The safe contract is the same shape as Modelo 289:

- `verified=true` is accepted only with `source_hash` and `capture_date`.
- `verified=false`, `safe_to_answer=false`, `review_required=true`,
  `source_hash=NULL`, `capture_date` present and an `evidence_limited` notice is
  accepted as explicit fail-closed state.

## Local Change

`scripts/maintenance/mcp_validation_suite.py` now separates:

- `modelo_202_all_profiles_loaded`: checks that the six expected profile rows
  are present.
- `modelo_202_profiles_verified_or_fail_closed_6`: checks that each expected
  row is either verified with normalized evidence or explicitly fail-closed.

`perfil_sociedad_valores_fiscal_routing_contract` now accepts Modelo 202 when
the routing item is either verified with evidence or explicitly fail-closed.

## Validation

Local:

- `python -m pytest scripts/tests/test_maintenance_agents.py -q` -> `21 passed`.
- `python -m py_compile scripts\maintenance\mcp_validation_suite.py` -> OK.

VPS after deployment of commit `8cf04d4`:

- `mcp_validation_suite.py --read-only --base-url http://api:8000`:
  `ok=false`, `checks=132`, `failures=6`.
- `modelo_202_all_profiles_loaded` passes with six loaded profiles.
- `modelo_202_profiles_verified_or_fail_closed_6` passes with six fail-closed
  profiles.
- `perfil_sociedad_valores_fiscal_routing_contract` passes with
  `modelo_202_accepted_states=['fail_closed']`.
- `mcp_deep_contract_audit.py --base-url http://api:8000`: `ok=false`,
  `checks=12`, `failures=3`.
- Remaining validation failures stay scoped to `sociedad_valores` verified
  threshold, RTS1/RTS2, CASP, `emisor_token`, profile-applicability leftovers
  for Modelo 303/RTS1 and aggregate coverage.

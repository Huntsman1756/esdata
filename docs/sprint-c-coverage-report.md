# Sprint C Coverage Report: Motor de Aplicabilidad por Perfil

Date: 2026-05-17

Scope: production applicability data and tool contracts created during Sprint C. Counts below come from production SQL on the active VPS after deploying branch `feat/sprint-c-motor-aplicabilidad`.

## Production Counts

| perfil | obligations | verified | evidence_limited | tools_registered |
|---|---:|---:|---:|---|
| `agencia_valores` | 26 | 17 | 9 | yes |
| `sgiic` | 13 | 11 | 2 | yes |
| `sociedad_valores` | 26 | 17 | 9 | yes |

Additional table counts:

| table | COUNT production | Notes |
|---|---:|---|
| `perfil_entidad` | 6 | Six active supervised entity profiles. |
| `obligacion_perfil` | 65 | Profile obligation matrix across `sociedad_valores`, `agencia_valores`, and `sgiic`. |
| `obligacion_fuente` | 120 | Traceable source rows linked to obligations. |

## SQL Evidence

```sql
SELECT perfil_codigo AS perfil,
       COUNT(1) AS obligaciones,
       COUNT(1) FILTER (WHERE verified) AS verified,
       COUNT(1) FILTER (WHERE NOT verified) AS evidence_limited
FROM obligacion_perfil
GROUP BY perfil_codigo
ORDER BY perfil_codigo;
```

Result:

| perfil | obligaciones | verified | evidence_limited |
|---|---:|---:|---:|
| `agencia_valores` | 26 | 17 | 9 |
| `sgiic` | 13 | 11 | 2 |
| `sociedad_valores` | 26 | 17 | 9 |

```sql
SELECT COUNT(1) AS perfil_entidad FROM perfil_entidad;
SELECT COUNT(1) AS obligacion_fuente FROM obligacion_fuente;
```

Result:

| metric | count |
|---|---:|
| `perfil_entidad` | 6 |
| `obligacion_fuente` | 120 |

## API Evidence

- `GET /v1/perfil` returns 6 profiles.
- `GET /v1/perfil/sociedad_valores` returns `obligaciones_total=26`.
- `GET /v1/perfil/sociedad_valores/obligaciones` returns `total=26`.
- `GET /v1/perfil/sociedad_valores/obligaciones?dominio=PBC_FT` returns `total=8`.
- `GET /v1/perfil/sociedad_valores/obligaciones/calendario` groups obligations by periodicity, with non-empty `anual` and `continua`.

## MCP Tool Contract

The following MCP-first profile tools are registered and validated:

| tool | purpose |
|---|---|
| `listar_perfiles_entidad` | Lists supervised entity profiles available in ESData. |
| `obtener_obligaciones_perfil` | Returns flat, source-traceable regulatory obligations for a profile and domain. |
| `calendario_obligaciones_perfil` | Returns profile obligations grouped by periodicity for operational planning. |

Contract guardrails:

- Every returned obligation must have `source_url`.
- `evidence_notice` is present in each response.
- `safe_to_answer=false` when unverified obligations exceed 30% of the response.
- `verified=true` is reserved for obligations traced to a loaded official norm/article and source URL.

## Validation Evidence

- Local targeted tests: `pytest apps/api/tests/test_mcp_tools_perfil.py apps/api/tests/test_perfil_router.py -q` -> `13 passed`.
- Production `mcp_validation_suite.py --read-only --base-url http://api:8000` from the `ops` container with API keys injected -> `ok=true`.
- Production `mcp_deep_contract_audit.py --base-url http://api:8000` from the `ops` container with API keys injected -> `ok=true`.

## Caveats

- Sprint C is an applicability matrix, not a full legal opinion engine. Conditional obligations remain `completeness='parcial'` and should be interpreted with the condition in `notas`.
- `agencia_valores` and `sgiic` were seeded from the `sociedad_valores` base with profile-specific caveats; further entity-specific refinement should happen in later sprints.
- The next high-impact extension is Sprint D: ESMA ISRB granular loading for MiFIR, EMIR, DORA and MiCA obligations.

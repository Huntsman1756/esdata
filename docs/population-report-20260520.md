# Population Report - A-14

Date: 2026-05-20
Branch: `fix/full-audit-stale-workers-20260520`
Baseline: v1.13.0
VPS: `root@212.227.227.64` via local SSH alias `steamcases-vps`

## Scope

A-14 is the final population snapshot for the stale-worker audit.

This report consolidates counts and baseline status only. It does not reopen the broader validation suites from A-06..A-13.

## Result

A-14 result: PASS.

Baseline confirmed:

```text
obligacion_perfil: 190 total / 190 verified
profiles: 8
MiCA profiles: casp 8/8, emisor_token 8/8
API health: ok
database health: ok
Alertmanager active alerts: []
```

## Primary Table Counts

| table | rows |
|---|---:|
| `articulo` | 1,970 |
| `version_articulo` | 3,512 |
| `norma` | 64 |
| `obligacion_perfil` | 190 |
| `perfil_entidad` | 8 |
| `documento_interpretativo` | 19,619 |
| `aeat_modelo` | 219 |
| `modelo_articulo` | 51 |
| `modelo_campana` | 236 |
| `modelo_campana_operativa` | 24 |
| `modelo_casilla` | 31,685 |
| `modelo_clave` | 179 |
| `modelo_instruccion` | 70 |
| `modelo_normativa` | 26 |
| `sync_log` | 1,781 |
| `query_audit_log` | 8,340 |

Note: `sync_log` row count is not expected to match the max ID because sequences can have gaps.

## Obligations Baseline

| metric | count |
|---|---:|
| total obligations | 190 |
| `verified=true` | 190 |
| not verified | 0 |

By profile:

| perfil_codigo | total | verified |
|---|---:|---:|
| `agencia_valores` | 38 | 38 |
| `casp` | 8 | 8 |
| `eaf` | 25 | 25 |
| `emisor_token` | 8 | 8 |
| `empresa_servicios_pago` | 13 | 13 |
| `entidad_credito` | 34 | 34 |
| `sgiic` | 26 | 26 |
| `sociedad_valores` | 38 | 38 |

## MiCA Baseline

MiCA Sprint M/N baseline remains intact:

| profile | obligations | verified |
|---|---:|---:|
| `casp` | 8 | 8 |
| `emisor_token` | 8 | 8 |

Canonical weak duplicate check:

| codigo | celex | tipo_norma |
|---|---|---|
| `32022R2554` | `32022R2554` | `reglamento_ue` |
| `32023R1114` | `32023R1114` | `reglamento_ue` |

No weak duplicate rows for `DORA_2022_2535` or `MICA_2023_1114` were present in the A-14 query.

## AEAT Baseline

A-13 closed with verify-first and no reseed. A-14 confirms the same population baseline:

| table | rows |
|---|---:|
| `aeat_modelo` | 219 |
| `modelo_articulo` | 51 |
| `modelo_casilla` | 31,685 |
| `modelo_clave` | 179 |
| `modelo_instruccion` | 70 |

A-13 integrity checks remain the controlling evidence for AEAT:

- `aeat_modelo`: 0 critical nulls and 0 duplicate `codigo`.
- `modelo_articulo`: 0 critical nulls, 0 orphan `modelo_id`, 0 orphan `articulo_id`, 0 duplicate `(modelo_id, articulo_id)`.
- No seed was executed in A-13 or A-14.

## Latest Sync Log Entries

Latest 10 rows at snapshot time:

| id | worker | status | finished_at UTC | errors |
|---:|---|---|---|---:|
| 1783 | `worker-boe` | `ok` | 2026-05-20 19:09:11 | 0 |
| 1782 | `worker-boe` | `ok` | 2026-05-20 18:01:07 | 0 |
| 1781 | `worker-boe` | `ok` | 2026-05-20 17:56:57 | 0 |
| 1780 | `worker-boe` | `ok` | 2026-05-20 17:48:05 | 0 |
| 1779 | `worker-boe` | `ok` | 2026-05-20 17:41:23 | 0 |
| 1778 | `worker-boe` | `ok` | 2026-05-20 17:34:15 | 0 |
| 1777 | `worker-boe` | `ok` | 2026-05-20 16:26:14 | 0 |
| 1776 | `worker-boe` | `ok` | 2026-05-20 16:21:58 | 0 |
| 1775 | `worker-boe` | `ok` | 2026-05-20 16:13:06 | 0 |
| 1774 | `worker-boe` | `ok` | 2026-05-20 16:06:24 | 0 |

The latest rows are dominated by `worker-boe`, which is expected for the active continuous BOE worker.

## Operational Snapshot

`/health`:

```json
{"status":"ok","database":"ok"}
```

Alertmanager active alerts:

```json
[]
```

## Evidence

Captured on VPS:

```text
/root/a14-population-report-20260520/evidence_counts.txt
/root/a14-population-report-20260520/evidence_ops.txt
```

## Closeout

The audit branch has completed A-04 through A-14.

Remaining known caveats are documented in their source reports:

- `cron-eu-sanctions-weekly` upstream `HTTP 403`, not stale-worker silence.
- `scripts/tests/test_compose_env_example.py` has pre-existing env-template drift from A-10b.
- Workers/cron still use the privileged ingestion DB role; API runtime is least-privileged since A-10b.

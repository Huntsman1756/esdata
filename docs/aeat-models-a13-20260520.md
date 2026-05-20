# A-13 AEAT Models Verify-First

Date: 2026-05-20
Branch: `fix/full-audit-stale-workers-20260520`
VPS: `root@212.227.227.64` via local SSH alias `steamcases-vps`

## Scope

A-13 verified the current production state of AEAT model tables before touching any seed.

Rule for this story:

- If `aeat_modelo` and `modelo_articulo` are populated and coherent, mark OK without reseeding.
- Run seeds only if the tables are empty or FK/logical integrity is broken.

No seed was executed.

## Counts

Production counts:

| table | rows |
|---|---:|
| `aeat_modelo` | 219 |
| `modelo_articulo` | 51 |
| `modelo_campana` | 236 |
| `modelo_campana_operativa` | 24 |
| `modelo_casilla` | 31,685 |
| `modelo_clave` | 179 |
| `modelo_instruccion` | 70 |
| `modelo_normativa` | 26 |

Both A-13 target tables are populated.

## Schema Notes

The production `aeat_modelo` table does not have a `tipo` column. Critical model classification is held through columns such as `codigo`, `nombre`, `impuesto`, `activo`, `url_info`, `url_listado`, `slug_portal`, and lifecycle fields.

The production `modelo_articulo` table links by IDs:

- `modelo_id -> aeat_modelo(id)`
- `articulo_id -> articulo(id)`

It does not use `modelo_codigo` directly.

## Integrity Checks

`aeat_modelo` critical nulls:

| check | count |
|---|---:|
| missing `codigo` | 0 |
| missing `nombre` | 0 |
| missing `activo` | 0 |
| missing `impuesto` | 0 |
| missing `url_info` | 0 |

`aeat_modelo` duplicate `codigo`: 0.

`modelo_articulo` critical nulls:

| check | count |
|---|---:|
| missing `modelo_id` | 0 |
| missing `articulo_id` | 0 |
| missing `fuente` | 0 |
| missing `norma` | 0 |
| missing `numero` | 0 |
| missing `metodo_enlace` | 0 |

`modelo_articulo` FK/logical checks:

| check | count |
|---|---:|
| orphan `modelo_id` | 0 |
| orphan `articulo_id` | 0 |
| duplicate `(modelo_id, articulo_id)` | 0 |

Database constraints also exist:

- `modelo_articulo_modelo_id_fkey`: `modelo_id` references `aeat_modelo(id)`.
- `modelo_articulo_articulo_id_fkey`: `articulo_id` references `articulo(id)`.
- `modelo_articulo_pkey`: primary key `(modelo_id, articulo_id)`.
- `aeat_modelo_codigo_key`: unique `codigo`.

## Worker Freshness

Latest AEAT model worker telemetry:

| worker | latest id | status | errors |
|---|---:|---|---:|
| `cron-modelos-daily` | 1766 | `ok` | 0 |
| `worker-modelos` | 1724 | `ok` | 0 |

Older `AdminShutdown` errors were present during redeploy windows, but latest runs are healthy.

## Decision

A-13 result: PASS.

No reseed was needed or executed.

The existing data is populated and coherent enough for the A-13 acceptance criteria.

## Evidence

Captured on VPS:

```text
/root/a13-aeat-models-20260520/evidence_final.txt
/root/a13-aeat-models-20260520/evidence_constraints.txt
```

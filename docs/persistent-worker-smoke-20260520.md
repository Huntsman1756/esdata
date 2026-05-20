# Persistent Worker Smoke - 2026-05-20

## Status

Blocked. A-04 is not marked as passed.

Ralph did not execute A-04 correctly because it read historical `<promise>COMPLETE</promise>` entries from `progress.txt` and exited on the completed Sprint N context. The smoke was therefore run manually against the VPS with a reproducible harness:

`scripts/maintenance/a04_persistent_worker_smoke.sh`

VPS target:

`root@212.227.227.64` (`/srv/esdata`)

Compose command:

`docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml`

## Discovery

Persistent workers were derived from live Compose output:

`docker compose --profile cron config --format json`

Selection rule:

`service name starts with worker- and profiles does not include cron`

Real persistent worker count: **14**

## Persistent Worker List

1. `worker-aepd`
2. `worker-bde`
3. `worker-bdns`
4. `worker-boe`
5. `worker-boe-modelos`
6. `worker-borme`
7. `worker-cdi`
8. `worker-cendoj`
9. `worker-cnmv`
10. `worker-dgt`
11. `worker-eurlex`
12. `worker-modelos`
13. `worker-sepblac`
14. `worker-teac`

## Smoke Results

The harness used each service's `WORKER_CMD` from Compose and executed:

`docker compose run -T --rm <service> sh -lc "<WORKER_CMD> --run-once"`

Important harness finding: `docker compose run <service> --run-once` is wrong for this Compose shape because it replaces the service command and Docker tries to execute `--run-once` as a binary.

| service | exit_code | run_once_supported | outcome |
|---|---:|---|---|
| `worker-aepd` | 0 | yes | ok |
| `worker-bde` | 0 | yes | ok |
| `worker-bdns` | 0 | yes | ok |
| `worker-boe` | 0 | yes | ok |
| `worker-boe-modelos` | 0 | yes | ok |
| `worker-borme` | 0 | yes | ok |
| `worker-cdi` | 0 | yes | ok |
| `worker-cendoj` | 0 | yes | ok |
| `worker-cnmv` | 124 | yes | timeout_300s |
| `worker-dgt` | 124 | yes | timeout_300s |
| `worker-eurlex` | 1 | yes | failed |
| `worker-modelos` | 124 | yes | timeout_300s |
| `worker-sepblac` | 0 | yes | ok |
| `worker-teac` | 0 | yes | ok |

Summary:

- Persistent workers: `14`
- `--run-once` unsupported: `0`
- OK within 300s: `10`
- Timeout at 300s: `3`
- Failed: `1`

## Blockers

### `worker-eurlex`

Status after A-04b: **fixed and verified on VPS**.

Verification:

- Branch deployed on VPS: `fix/full-audit-stale-workers-20260520`
- Worker image rebuilt: `worker-eurlex`
- Command: `docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml run -T --rm worker-eurlex sh -lc 'python eurlex.py --run-once'`
- Exit code: `0`
- Output: `[run-once] Bloques: 0, Articulos: 0, Normas: 32, Nuevos SPARQL: 0`
- `sync_log`: row `1730`, `worker='cron-eurlex-weekly'`, `status='ok'`, `errors=0`
- Canonical row preserved: `boe_id='EUR-CELEX-32014L0065'`, `codigo='32014L0065'`

Original failure:

`worker-eurlex` fails with a database integrity error:

`duplicate key value violates unique constraint "norma_boe_id_key"`

The conflicting key is:

`boe_id=EUR-CELEX-32014L0065`

The worker attempts to insert/update:

`codigo=MIFID2_2014_65`

Current corpus has already been normalized to canonical CELEX rows in later sprints, so this looks like legacy EUR-Lex seed/upsert logic colliding with current canonical `norma` uniqueness.

Secondary failure during error handling:

`duplicate key value violates unique constraint "uq_dead_letter_worker_entity"`

The worker then fails while trying to insert the same dead-letter row:

`(worker_name, entity_id)=(eurlex, eurlex)`

### Long-running workers

These support `--run-once` but exceeded the 300 second smoke timeout:

- `worker-cnmv`
- `worker-dgt`
- `worker-modelos`

Observed behavior is not silent: logs show active upstream/API work. For example, `worker-dgt` was discovering DGT consultas (`V0144-26` through `V0182-26`) and `worker-modelos` was actively crawling AEAT model pages.

One orphaned `python dgt.py --run-once` process remained after timeout and was killed manually.

## A-05 Implication

A-05 must reuse the corrected Compose pattern:

`docker compose run -T --rm <service> sh -lc "<WORKER_CMD> --run-once" < /dev/null`

It should not use:

`docker compose run --rm <service> --run-once`

For cron services, the `WORKER_CMD` already includes `--run-once`, so A-05 should execute the cron service command as configured and avoid appending a second `--run-once`.

## Decision Needed

Before marking A-04 passed:

1. Fix or explicitly defer `worker-eurlex` duplicate-key behavior.
2. Decide whether the smoke timeout for long-running workers should be raised, or whether those workers need a bounded smoke mode.

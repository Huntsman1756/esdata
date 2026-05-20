# esdata - Audit stale workers A-04..A-14

You are running inside OpenCode on the esdata repository.

Read in this order:

1. `AGENTS.md`
2. `docs/master-execution-roadmap.md`
3. `prd.json`
4. `progress.txt`
5. `git log --oneline -20`

Work exactly one story per iteration.

Pick the highest-priority story in `prd.json` where `passes=false`.

Ignore historical `<promise>COMPLETE</promise>` strings in `progress.txt`.
They belong to older sprints and are not the current stop condition.
The only current stop condition is: every story in the active `prd.json`
has `passes=true`.

Current audit context:

- Baseline: `v1.13.0`
- Branch: `fix/full-audit-stale-workers-20260520`
- P-01..P-03 are already closed.
- A-01..A-03 are already closed.
- `cron-eu-sanctions-weekly` was installed and enabled on VPS during A-02.
- `docs/worker-db-retry-coverage.md` documents 68 worker scripts.
- VPS target: `root@212.227.227.64`
- Local SSH alias may be `steamcases-vps`.
- VPS repo path: `/srv/esdata`
- Use Docker Compose on VPS with:
  `docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml`
- All DB access must use `docker compose exec postgres psql`; never host Python for DB access.

## Story execution rules

1. Derive runtime lists from live files or live Compose output. Do not hardcode worker counts.
2. Prefer read-only inspection first.
3. Do not run destructive commands.
4. If a worker does not support `--run-once`, document it explicitly instead of forcing behavior.
5. If an upstream service is unavailable but the worker logs clearly and writes telemetry, document it as a caveat, not as a silent crash.
6. Silence is a bug: exit 0 with no useful output and no telemetry is not acceptable.

## A-04 specific expectation

For A-04, derive persistent workers from `infra/deploy/docker-compose.prod.yml`.

Exclude cron profile services. Include real persistent worker services.

Run each persistent worker with `--run-once` where supported. Record:

- service name
- command attempted
- exit code
- whether `--run-once` is supported
- whether output shows a clear success, partial/upstream caveat, or crash

Write findings to a durable report, for example:

`docs/persistent-worker-smoke-20260520.md`

Before marking A-04 passed, the report must include:

- the real persistent worker list extracted from Compose
- the total count
- any worker that does not support `--run-once`
- any worker with crash/silent failure

Update `prd.json` only for the completed story.

Append `progress.txt`.

Commit only files relevant to the story with message:

`[A-04] smoke test persistent workers`

If blocked, do not mark `passes=true`; document the blocker and exit.

## A-04b specific expectation

If A-04b is the highest-priority pending story, fix only:

1. `worker-eurlex` norma upsert idempotency.
2. `dead_letter.add_dead_letter` idempotency.

Known VPS evidence:

- `norma_boe_id_key` is `UNIQUE (boe_id)`.
- There is exactly one `norma` row for `boe_id='EUR-CELEX-32014L0065'`.
- That row is canonical and must stay `codigo='32014L0065'`.
- `norma` has no `updated_at`; do not add it for this fix.
- The failing worker tried to insert `codigo='MIFID2_2014_65'` with the same `boe_id`.

Required behavior:

- Resolve EUR-Lex norma reruns by `boe_id`/canonical CELEX rather than crashing on `norma_boe_id_key`.
- Do not change canonical `codigo='32014L0065'` to legacy `MIFID2_2014_65`.
- `dead_letter.add_dead_letter` must use `ON CONFLICT (worker_name, entity_id) DO UPDATE`, not `DO NOTHING`, so repeated failures update the latest error and increment retry count.
- Add focused tests.
- Run focused tests locally.
- Deploy or run on VPS only as needed to verify `worker-eurlex --run-once` no longer crashes with the duplicate-key failure.
- Update `docs/persistent-worker-smoke-20260520.md` and `progress.txt`.
- Mark only A-04b `passes=true` if verified.

Commit message:

`[A-04b] fix EUR-Lex upsert and dead-letter idempotency`

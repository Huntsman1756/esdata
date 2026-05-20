# A-11 Prometheus alert rules coverage

Date: 2026-05-20  
Branch: `fix/full-audit-stale-workers-20260520`  
VPS: `root@212.227.227.64` via local SSH alias `steamcases-vps`

## Scope

A-11 checked stale-worker alerting only:

- Prometheus rule syntax.
- Coverage for the four workers from the stale-worker incident/drift set.
- Use of real `sync_log.worker` names and status aliases.
- Thresholds aligned with the cadence policy.
- No stale rules hardcoded to dead or renamed worker names.

Out of scope: `compose.env.example` drift and unrelated worker/data findings.

## Prometheus rules

Command run on VPS:

```bash
docker compose --env-file /etc/esdata/esdata.env \
  -f infra/deploy/docker-compose.prod.yml \
  exec -T prometheus promtool check rules /etc/prometheus/alerts.yml
```

Result:

```text
Checking /etc/prometheus/alerts.yml
  SUCCESS: 7 rules found
```

`WorkerSilent` uses the exported status gauge:

```yaml
expr: worker_stale_status == 1
```

There are no per-worker stale expressions hardcoded for the four incident workers. Coverage comes from `/status`, which reads `sync_log`, applies `WORKER_CADENCE_CONFIG` and alias normalization, and exports `worker_stale_status{worker="..."}`.

## Four-worker coverage

Production `sync_log` contains all four target worker names:

| worker | latest sync_log id | latest status | stale metric |
|---|---:|---|---:|
| `cron-psd2-weekly` | 1763 | `ok` | 0 |
| `official-regulatory-references` | 1769 | `ok` | 0 |
| `cron-pgc-boe-monthly` | 1762 | `ok` | 0 |
| `cron-eu-sanctions-weekly` | 1753 | `error` | 0 |

Prometheus query result:

```text
worker_stale_status{worker="cron-psd2-weekly"} 0
worker_stale_status{worker="official-regulatory-references"} 0
worker_stale_status{worker="cron-pgc-boe-monthly"} 0
worker_stale_status{worker="cron-eu-sanctions-weekly"} 0
```

`cron-eu-sanctions-weekly` still records upstream `HTTP 403 Forbidden`, already documented in A-05/source backlog. It is not stale because it wrote fresh telemetry; this is an upstream-ingestion caveat, not a stale-worker alerting failure.

Alertmanager:

```text
[]
```

No active alerts were present during A-11.

## Cadence thresholds

The target workers are present in `WORKER_CADENCE_CONFIG` with thresholds equal to 1.5x the expected cadence:

| worker | trigger | expected cadence | stale threshold |
|---|---|---:|---:|
| `cron-psd2-weekly` | weekly | 168h | 252h |
| `official-regulatory-references` | weekly | 168h | 252h |
| `cron-pgc-boe-monthly` | monthly | 720h | 1080h |
| `cron-eu-sanctions-weekly` | weekly | 168h | 252h |

The focal test `apps/api/tests/test_worker_cadence.py` now pins these four entries.

## Name drift control

A-05 found six Compose-service to `sync_log.worker` mismatches. A-11 verifies alerting uses status metric labels derived from real `sync_log.worker` values, with explicit alias/exclusion handling:

| service | observed sync/status handling |
|---|---|
| `cron-aeat-current-daily` | `worker-aeat-current-designs` is aliased to `cron-aeat-current-daily` |
| `cron-boe-modelos-daily` | excluded as scheduler; status worker is `worker-boe-modelos` |
| `cron-esma-dlt-weekly` | aliased to `worker-esma-dlt` |
| `cron-esma-firds-daily` | aliased to `worker-esma-firds` |
| `cron-esma-mifir-reporting-weekly` | aliased to `worker-esma-mifir-reporting` |
| `cron-eurlex-market-monthly` | aliased to `worker-eurlex-market` |

The alert file itself does not hardcode the four stale-worker names or those six drift names for `WorkerSilent`; it evaluates the live `worker_stale_status` series. This avoids stale/dead alert rules when a Compose service writes a different canonical worker name.

## MCP transport note

`GET /mcp` without a valid MCP API key returns `401`. With a key and `Accept: text/event-stream`, a bare GET returns:

```text
HTTP 400
Bad Request: Missing session ID
```

This is expected for the stateful MCP transport: the client must establish/use a session before GET streaming. It is not an operational alert condition and should not be added to stale-worker alerting.

## Result

A-11 result: PASS.

Evidence captured on VPS:

```text
/root/a11-alert-rules-20260520/evidence.txt
```

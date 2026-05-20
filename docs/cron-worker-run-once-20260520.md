# Cron Worker Run-Once Smoke - 2026-05-20

## Scope

A-05 ran against the VPS at `root@212.227.227.64` from `/srv/esdata`.

The cron service list was derived from the live production Compose config:

```bash
docker compose --env-file /etc/esdata/esdata.env \
  -f infra/deploy/docker-compose.prod.yml \
  --profile cron config --format json
```

Minimum accepted telemetry threshold: `sync_log.id > 1623`.

## Result

`cron_service_count=28`.

All 28 cron services produced at least one new `sync_log` row with `id > 1623`.

The run surfaced three operational caveats:

- `cron-eurlex-weekly` initially failed because the cron image still contained pre-A-04b code. Rebuilding `cron-eurlex-weekly` fixed it; the rerun exited `0` and wrote `sync_log.id=1772`, `worker='cron-eurlex-weekly'`, `status='ok'`, `errors=0`.
- `cron-boe-daily` and `cron-modelos-daily` exceeded the 900s smoke timeout, but both wrote new sync telemetry. `cron-modelos-daily` later completed with `sync_log.id=1766`, `status='ok'`, `rows_processed=9126`.
- `cron-eu-sanctions-weekly` wrote telemetry but upstream returned `HTTP Error 403: Forbidden`; this is an explicit upstream failure, not a silent crash or DB/network failure.

No silent cron run was observed.

## Cron Services

1. `cron-aeat-current-daily`
2. `cron-aepd-weekly`
3. `cron-bde-weekly`
4. `cron-bdns-weekly`
5. `cron-boe-daily`
6. `cron-boe-diario-daily`
7. `cron-boe-modelos-daily`
8. `cron-borme-weekly`
9. `cron-cdi-weekly`
10. `cron-cendoj-weekly`
11. `cron-cnmv-weekly`
12. `cron-dgt-weekly`
13. `cron-esma-dlt-weekly`
14. `cron-esma-firds-daily`
15. `cron-esma-mifir-reporting-weekly`
16. `cron-eu-sanctions-weekly`
17. `cron-eurlex-market-monthly`
18. `cron-eurlex-weekly`
19. `cron-giin-monthly`
20. `cron-mica-weekly`
21. `cron-modelos-daily`
22. `cron-ofac-sdn-weekly`
23. `cron-pgc-boe-monthly`
24. `cron-psd2-weekly`
25. `cron-regulatory-daily`
26. `cron-sepblac-weekly`
27. `cron-teac-weekly`
28. `official-regulatory-references`

## Services Writing Telemetry Under Internal Worker Names

These services produced valid telemetry, but the `sync_log.worker` value is the internal worker name rather than the Compose service name:

| service | sync_log worker |
|---|---|
| `cron-aeat-current-daily` | `worker-aeat-current-designs` |
| `cron-boe-modelos-daily` | `worker-boe-modelos` |
| `cron-esma-dlt-weekly` | `worker-esma-dlt` |
| `cron-esma-firds-daily` | `worker-esma-firds` |
| `cron-esma-mifir-reporting-weekly` | `worker-esma-mifir-reporting` |
| `cron-eurlex-market-monthly` | `worker-eurlex-market` |

This is not a data loss problem, but alerting rules must account for these aliases if they alert by Compose service name.

## Verification Snapshot

New rows observed during and immediately after the sweep:

```text
1732 worker-aeat-current-designs    ok
1733 cron-aepd-weekly               partial
1734 cron-bde-weekly                ok
1735 cron-bdns-weekly               ok
1736 cron-boe-daily                 ok
1737 cron-boe-daily                 ok
1738 cron-boe-diario-daily          ok
1739 worker-boe-modelos             ok
1740 worker-boe-modelos             ok
1741 worker-boe-modelos             ok
1742 worker-boe-modelos             ok
1743 worker-boe-modelos             ok
1744 cron-borme-weekly              ok
1745 cron-cdi-weekly                ok
1746 cron-cendoj-weekly             ok
1748 cron-cnmv-weekly               ok
1749 cron-dgt-weekly                ok
1750 worker-esma-dlt                ok
1751 worker-esma-firds              ok
1752 worker-esma-mifir-reporting    ok
1753 cron-eu-sanctions-weekly       error (upstream 403)
1754 worker-eurlex-market           ok
1757 cron-giin-monthly              ok
1758 cron-mica-weekly               ok
1761 cron-ofac-sdn-weekly           ok
1762 cron-pgc-boe-monthly           ok
1763 cron-psd2-weekly               ok
1764 cron-regulatory-daily          ok
1765 cron-sepblac-weekly            ok
1766 cron-modelos-daily             ok
1768 cron-teac-weekly               ok
1769 official-regulatory-references ok
1772 cron-eurlex-weekly             ok
```

Additional `worker-boe` rows appeared during the sweep from BOE-backed jobs or the persistent worker; they are not counted as missing cron telemetry.

## Follow-Ups

- Backlog: verify that every cron image is rebuilt during main deploys, not only the API or persistent worker image. A-05 caught `cron-eurlex-weekly` running an old cron image after the `worker-eurlex` image had already been rebuilt.
- A-11: add an alias map for cron service name to `sync_log.worker` in stale-worker alert logic. The six observed aliases are listed above; alert rules that use Compose service names only will miss those workers.
- Add bounded smoke flags for long workers (`cron-boe-daily`, `cron-modelos-daily`) so A-05 can complete without waiting on full upstream work.
- Keep `cron-eurlex-weekly` rebuilt after EUR-Lex worker code changes; it uses a separate cron image from `worker-eurlex`.

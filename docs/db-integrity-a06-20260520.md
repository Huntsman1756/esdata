# DB Integrity A-06 - 2026-05-20

## Scope

A-06 ran against the VPS at `root@212.227.227.64` from `/srv/esdata`.

Command:

```bash
cat scripts/integrity-check.sql | docker compose --env-file /etc/esdata/esdata.env \
  -f infra/deploy/docker-compose.prod.yml \
  exec -T postgres psql -U esdata -d esdata -v ON_ERROR_STOP=1 -f -
```

## Checks Covered

- PostgreSQL FK constraints are validated.
- Defensive FK orphan scans include:
  - `version_articulo.articulo_id -> articulo.id`
  - `articulo.norma_id -> norma.id`
  - `obligacion_perfil.norma_codigo -> norma.codigo`
  - core AEAT/model/document relationship tables.
- Generic NULL scan over all public `NOT NULL` columns.
- Critical empty-content checks include:
  - `norma.codigo`
  - `norma.titulo`
  - `norma.boe_id`
  - `version_articulo.texto`
  - `obligacion_perfil.source_url`
  - core AEAT/document audit columns.
- Logical duplicate checks include:
  - `articulo(norma_id, numero)`
  - `aeat_modelo(codigo)`
  - `documento_interpretativo(referencia)`
  - core model relationship keys.

The current schema does not have `articulo.source_url`, `articulo.boe_reference`, or `articulo.texto` columns. Article text is versioned in `version_articulo`; authoritative identifiers live on `norma`.

## Production Finding Fixed

Initial run failed with one blocking finding:

```text
version_articulo.id=6785
norma=32014L0065
boe_id=EUR-CELEX-32014L0065
articulo=95 bis
vigente_desde=2026-06-06
boe_bloque_id=official:32014L0065:90
texto_len=0
```

Fix:

- `apps/workers/eurlex.py` now skips empty official EUR-Lex blocks before inserting `articulo` or `version_articulo`.
- Added focused test coverage in `apps/workers/tests/test_eurlex.py`.
- Rebuilt `worker-eurlex` and `cron-eurlex-weekly` images on VPS.
- Removed the existing empty historical row:
  - deleted `version_articulo.id=6785`
  - deleted now-orphaned `articulo.id=76592`, `numero='95 bis'`

## Final Result

Final run:

```text
Integrity failures (blocking):
 check_group | check_name | failing_rows
-------------+------------+--------------
(0 rows)

PASS integrity checks
```

Non-blocking warnings:

```text
documento_interpretativo.texto empty on partial rows: 6
aeat_modelo.periodo empty: 75
```

Both warnings are expected by the script:

- partial interpretative documents preserve official source URLs and are not complete text rows;
- `aeat_modelo.periodo` is nullable because not every AEAT model page exposes cadence.

# esdata - Sprint K: DORA RTS/ITS operativo

Pattern: Ralph, one story per iteration.

Prerequisite: main=v1.9.0, 3124 passed, 151/151 verified.

Confirmed DORA CELEX:
- 32022R2554: base DORA, already loaded.
- 32024R1774: delegated RTS for ICT risk management framework and simplified framework.
- 32024R1773: delegated RTS for ICT third-party contractual arrangements.

Do not load any other DORA RTS/ITS CELEX without verifying HTTP 200 and DORA content on EUR-Lex first.

Current Sprint K gaps:
- Remove weak duplicate `DORA_2022_2535`.
- Load `32024R1774` and `32024R1773` in `norma`.
- Add DORA obligations for `agencia_valores`.
- Add conditional DORA obligations for `eaf` with microenterprise exemption notes.
- Add DORA art. 28 and art. 30 third-party ICT obligations for all six profiles.
- Replace DORA article ranges with specific anchor articles.
- Extend `mcp_validation_suite.py` and `mcp_deep_contract_audit.py`.

Operating rules:
- All DB access via `docker compose exec postgres psql`.
- On VPS use `docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml`.
- Docker services are `api` and `ops`; there is no `worker` service.
- One story per iteration, no exceptions.

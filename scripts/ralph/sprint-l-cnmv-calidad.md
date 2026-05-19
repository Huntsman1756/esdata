# esdata - Sprint L: CNMV calidad y aplicabilidad

Pattern: Ralph, one story per iteration.

Prerequisite: main=v1.10.0, 3124 passed, 168/168 verified.

Decision: Option C. Do not create CNMV registry tables in this sprint. `registros_oficiales` stays `configured_but_unavailable`; candidate Sprint M.

Sprint L scope:
- Confirm and document `documento_interpretativo.sujeto_obligado` storage.
- Populate CNMV document applicability for the 141 loaded CNMV rows.
- Link selected `normativa_esi_cnmv` rows to `obligacion_perfil`.
- Link all `modelo_esi_cnmv` rows through `cnmv_obligation_link`.
- Add `/v1/cnmv/perfil/{perfil_codigo}`.
- Expose the CNMV perfil document retrieval as an MCP tool.
- Add validation suite checks.

Operating rules:
- All DB access via `docker compose exec postgres psql`.
- On VPS use `docker compose --env-file /etc/esdata/esdata.env -f infra/deploy/docker-compose.prod.yml`.
- Docker services are `api` and `ops`; there is no `worker` service.
- One story per iteration, no exceptions.

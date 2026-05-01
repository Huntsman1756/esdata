PYTEST ?= pytest
NPM ?= npm
RUFF ?= ruff
ALEMBIC ?= alembic

.PHONY: help test test-api test-workers test-web lint lint-python build-web api worker-boe worker-dgt worker-teac worker-modelos bootstrap-db db-upgrade db-current smoke-check eval eval-local eval-summary eval-gate

help:
	@printf "Targets:\n"
	@printf "  test            Run API, workers and web tests\n"
	@printf "  test-api        Run API tests\n"
	@printf "  test-workers    Run worker tests\n"
	@printf "  test-web        Run web tests\n"
	@printf "  lint            Run Python lint\n"
	@printf "  build-web       Build Next.js web app\n"
	@printf "  api             Start API locally\n"
	@printf "  worker-boe      Run BOE worker once\n"
	@printf "  worker-dgt      Run DGT worker once\n"
	@printf "  worker-teac     Run TEAC worker once\n"
	@printf "  worker-modelos  Run modelos worker once\n"
	@printf "  bootstrap-db    Apply minimal SQL bootstrap + Alembic migrations\n"
	@printf "  db-upgrade      Apply Alembic migrations to DATABASE_URL\n"
	@printf "  db-current      Show current Alembic revision\n"
	@printf "  smoke-check     Run reusable API smoke checks (requires API_BASE)\n"
	@printf "  eval            Run phase 3 benchmark against running API (ESDATA_API_URL)\n"
	@printf "  eval-local      Run phase 3 benchmark in-process (SQLite test DB)\n"
	@printf "  eval-ci         Run eval unit tests (fast, no API needed)\n"
	@printf "  eval-gate       Run benchmark and enforce quality gate (fails if score < 0.80)\n"
	@printf "  eval-summary    Print summary from latest eval result JSON without re-running\n"

test: test-api test-workers test-web

test-api:
	$(PYTEST) apps/api/tests/ -v --tb=short

test-workers:
	$(PYTEST) apps/workers/tests/ -v --tb=short

test-web:
	$(NPM) --prefix apps/web test

lint: lint-python

lint-python:
	$(RUFF) check apps/ verify_railway.py

build-web:
	$(NPM) --prefix apps/web run build

api:
	uvicorn main:app --app-dir apps/api --host 0.0.0.0 --port 8000

worker-boe:
	python apps/workers/boe.py --run-once

worker-dgt:
	python apps/workers/dgt.py --run-once

worker-teac:
	python apps/workers/teac.py --run-once

worker-modelos:
	python apps/workers/modelos.py --run-once

bootstrap-db:
	psql "$(DATABASE_URL)" -f infra/sql/init.sql
	$(ALEMBIC) upgrade heads

db-upgrade:
	$(ALEMBIC) upgrade heads

db-current:
	$(ALEMBIC) current

smoke-check:
	python scripts/ops/smoke-check.py --base-url "$(API_BASE)"

eval:
	@python scripts/eval/eval_phase3.py --base-url "$(ESDATA_API_URL:http://localhost:8001)"

eval-local:
	@python scripts/eval/eval_phase3.py --local

eval-summary:
	@python scripts/eval/eval_phase3.py --summary-only

eval-ci:
	@$(PYTEST) scripts/tests/test_eval_phase3.py -v --tb=short

eval-gate:
	@python scripts/eval/eval_phase3.py --base-url "$(ESDATA_API_URL:http://localhost:8001)" --baseline scripts/baseline.json

FROM python:3.12-slim@sha256:46cb7cc2877e60fbd5e21a9ae6115c30ace7a077b9f8772da879e4590c18c2e3 AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*

RUN addgroup --system app && adduser --system --ingroup app app

COPY libs/python/esdata_common /tmp/esdata_common

COPY apps/api/requirements.txt /tmp/requirements.txt
RUN sed -i '/esdata_common/d' /tmp/requirements.txt && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    cp -r /tmp/esdata_common /usr/local/lib/python3.12/site-packages/esdata_common

COPY apps/api/ /app
COPY alembic.ini /app/alembic.ini
COPY alembic/ /app/alembic/
COPY docs/openapi-gpt.json /app/docs/openapi-gpt.json

USER app

EXPOSE 8000

CMD ["sh", "-c", "echo '[MIGRATION] Running alembic upgrade heads...' && alembic upgrade heads && echo '[MIGRATION] Alembic upgrade completed successfully.' && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY libs/python/esdata_common /tmp/esdata_common

COPY apps/api/requirements.txt /tmp/requirements.txt
RUN sed -i '/esdata_common/d' /tmp/requirements.txt && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    cp -r /tmp/esdata_common /usr/local/lib/python3.12/site-packages/esdata_common

COPY apps/api/ /app

USER app

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

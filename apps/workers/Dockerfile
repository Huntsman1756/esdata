FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY libs/python/esdata_common /tmp/esdata_common
COPY apps/workers/requirements.txt /tmp/requirements.txt
RUN sed -i '/esdata_common/d' /tmp/requirements.txt && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    cp -r /tmp/esdata_common /usr/local/lib/python3.12/site-packages/esdata_common

COPY apps/workers/ /app

USER app

CMD ["sh", "-c", "WORKER_CMD=${WORKER_CMD:-python boe.py}; exec python entrypoint.py"]

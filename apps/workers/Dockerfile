FROM python:3.12-slim

WORKDIR /app

COPY . /app

RUN if [ -f /app/requirements.txt ]; then pip install --no-cache-dir -r /app/requirements.txt; else pip install --no-cache-dir -r /app/apps/workers/requirements.txt; fi

CMD ["sh", "-c", "WORKER_CMD=${WORKER_CMD:-python boe.py}; if [ -f /app/dgt.py ]; then cd /app && exec sh -c \"$WORKER_CMD\"; else cd /app/apps/workers && exec sh -c \"$WORKER_CMD\"; fi"]

FROM python:3.12-slim

WORKDIR /app

COPY . /app

RUN if [ -f /app/requirements.txt ]; then pip install --no-cache-dir -r /app/requirements.txt; else pip install --no-cache-dir -r /app/apps/workers/requirements.txt; fi

CMD ["sh", "-c", "if [ -f /app/boe.py ]; then python /app/boe.py; else cd /app/apps/workers && python boe.py; fi"]

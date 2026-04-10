FROM python:3.12-slim

WORKDIR /app

COPY apps/workers/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY apps/workers /app/workers

CMD ["python", "-m", "workers.boe"]

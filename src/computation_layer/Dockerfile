FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir psycopg[binary] fastapi

COPY computation_layer.py /app/computation_layer.py

ENV DB_DSN=postgresql://admin:admin@postgres:5432/mydb

CMD ["python", "/app/computation_layer.py"]
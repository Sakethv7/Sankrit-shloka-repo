FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir mlflow==2.12.2 psycopg2-binary boto3

EXPOSE 5000

CMD ["/bin/sh", "-c", "mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri ${MLFLOW_BACKEND_STORE_URI} --default-artifact-root ${MLFLOW_ARTIFACT_ROOT}"]

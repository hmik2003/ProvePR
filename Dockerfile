# ProvePR — single image for local Docker + Cloud Run
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    HERMES_ENABLE_PROJECT_PLUGINS=1 \
    PORT=8080 \
    PROVEPR_HTTP_HOST=0.0.0.0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY .hermes ./.hermes

EXPOSE 8080

CMD ["python", "-m", "provepr", "serve"]

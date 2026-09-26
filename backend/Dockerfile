# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

# No secrets are baked into the image. All runtime configuration is supplied
# via environment variables at container start (see docker-compose.yml / .env).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System dependencies for PDF parsing and OCR (tesseract-ocr, poppler-utils)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

# Documented default; the actual bound port comes from the required
# BACKEND_PORT environment variable at runtime.
EXPOSE 8000

# Container-level health check (liveness). Uses stdlib so no extra packages
# are required. Reads BACKEND_PORT from the environment.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os,urllib.request,sys; \
url='http://127.0.0.1:%s/api/v1/health' % os.environ['BACKEND_PORT']; \
sys.exit(0 if urllib.request.urlopen(url, timeout=4).status==200 else 1)" || exit 1

# Bind to the required BACKEND_PORT (shell form so the variable is expanded).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}"]

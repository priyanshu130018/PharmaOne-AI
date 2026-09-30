# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

# No secrets are baked into the image. All runtime configuration is supplied
# via environment variables at container start (see docker-compose.yml / .env).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

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

# Execute entrypoint: wait for DB, run migrations, seed data, and start Uvicorn.
CMD ["python", "-m", "app.scripts.entrypoint"]

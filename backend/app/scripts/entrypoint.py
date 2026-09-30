"""Container entrypoint script for PharmaOne-AI Backend.

Handles:
1. Waiting for PostgreSQL database connection.
2. Running Alembic migrations to bring the database schema to head.
3. Seeding canonical Connected QMS demo data idempotently.
4. Launching the Uvicorn ASGI server.
"""

import asyncio
import logging
import os
import re
import subprocess
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("entrypoint")


async def wait_for_db(max_retries: int = 30, delay: float = 2.0) -> bool:
    """Attempt connecting to the database using the configured DATABASE_URL."""
    settings = get_settings()
    safe_url = re.sub(r":([^@]+)@", ":***@", settings.DATABASE_URL)
    logger.info("Verifying database connectivity at %s...", safe_url)

    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection successfully established.")
            await engine.dispose()
            return True
        except Exception as e:
            logger.warning("Waiting for database (attempt %d/%d): %s", attempt, max_retries, e)
            await asyncio.sleep(delay)

    await engine.dispose()
    return False


def check_database_url():
    """Verify and log the database connection target."""
    settings = get_settings()
    safe_url = re.sub(r":([^@]+)@", ":***@", settings.DATABASE_URL)
    logger.info("Configured database connection target: %s", safe_url)


def run():
    logger.info("==================================================")
    logger.info("  PharmaOne-AI Container Startup Sequence")
    logger.info("==================================================")

    check_database_url()

    # 1. Wait for Database
    if not asyncio.run(wait_for_db()):
        logger.error("Database connection timed out. Exiting.")
        sys.exit(1)

    # 2. Run Database Migrations
    auto_migrate = os.environ.get("AUTO_MIGRATE", "true").lower() in ("true", "1", "yes")
    if auto_migrate:
        logger.info("Running database migrations (alembic upgrade head)...")
        res = subprocess.run(["alembic", "upgrade", "head"])
        if res.returncode != 0:
            logger.error("Alembic migration failed with code %d.", res.returncode)
            sys.exit(res.returncode)
        logger.info("Alembic migrations completed successfully.")
    else:
        logger.info("AUTO_MIGRATE is false; skipping migrations.")

    # 3. Seed Canonical QMS Data
    auto_seed = os.environ.get("AUTO_SEED", "true").lower() in ("true", "1", "yes")
    if auto_seed:
        logger.info("Seeding canonical Connected QMS data...")
        res = subprocess.run([sys.executable, "-m", "app.scripts.seed_qms_data"])
        if res.returncode != 0:
            logger.error("Database seeding failed with code %d.", res.returncode)
            sys.exit(res.returncode)
        logger.info("Canonical demo data verified and seeded successfully.")
    else:
        logger.info("AUTO_SEED is false; skipping seeding.")

    # 4. Start Uvicorn Server
    port = int(os.environ.get("BACKEND_PORT", 8000))
    logger.info("Starting FastAPI application via Uvicorn on 0.0.0.0:%d...", port)
    sys.stdout.flush()
    sys.stderr.flush()

    if hasattr(os, "execvp"):
        os.execvp("uvicorn", ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port)])
    else:
        import uvicorn
        uvicorn.run("app.main:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()

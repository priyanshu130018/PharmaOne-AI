from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.schemas.common import HealthStatus, ReadinessStatus

router = APIRouter(tags=["health"])

API_VERSION = "0.1.0"


@router.get("/health", response_model=HealthStatus, summary="Liveness probe")
async def health() -> HealthStatus:
    """Liveness check. Always returns quickly and does not touch the database,
    so the container is reported healthy even if the DB is briefly unreachable."""
    settings = get_settings()
    return HealthStatus(status="ok", environment=settings.ENVIRONMENT, version=API_VERSION)


@router.get("/health/ready", response_model=ReadinessStatus, summary="Readiness probe")
async def readiness() -> ReadinessStatus:
    """Readiness check. Verifies the database connection so orchestrators can
    decide whether to route traffic to this instance."""
    database = "unavailable"
    status = "degraded"
    try:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            await session.execute(text("SELECT 1"))
        database = "connected"
        status = "ready"
    except Exception:  # noqa: BLE001 - readiness must never raise
        database = "unavailable"
        status = "degraded"

    return ReadinessStatus(
        status=status,
        database=database,
        checked_at=datetime.now(timezone.utc),
    )

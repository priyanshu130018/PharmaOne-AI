"""Pytest fixtures and test-only configuration.

Test infrastructure is the *only* place we set configuration values inline —
application code never does. Here we populate the required environment
variables with harmless test placeholders and point the database at a local
SQLite file so the suite runs with no external services.
"""

import os
import pathlib
import sys
import uuid

# Ensure the backend package root is importable regardless of the caller's cwd.
BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

_TEST_DB_PATH = BACKEND_ROOT / "test_pharmaone.db"

# Populate required env BEFORE importing anything that reads settings.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("BACKEND_PORT", "8000")
os.environ.setdefault("API_BASE_URL", "http://testserver")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TEST_DB_PATH.as_posix()}")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("GROQ_MODEL", "openai/gpt-oss-20b")
os.environ.setdefault("HUGGINGFACE_API_KEY", "test-hf-key")
os.environ.setdefault("MAX_UPLOAD_SIZE_BYTES", "10485760")
os.environ.setdefault("OCR_ENABLED", "true")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from sqlalchemy import text
from app.db.session import dispose_engine, get_engine, get_sessionmaker  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, Company, CompanyMembership, Profile, Site  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _prepare_database():
    """Create a fresh schema for each test, seed default demo organizations, then tear it down."""
    engine = get_engine()
    async with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            await conn.execute(text("PRAGMA foreign_keys = OFF;"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        if engine.dialect.name == "sqlite":
            await conn.execute(text("PRAGMA foreign_keys = ON;"))

    # Seed test users and organizations
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        c1 = Company(id=uuid.uuid4(), name="Vasundha Pharma Chem Limited", status="active")
        c2 = Company(id=uuid.uuid4(), name="Competitor Pharma Limited", status="active")
        db.add_all([c1, c2])
        await db.flush()

        s1 = Site(id=uuid.uuid4(), company_id=c1.id, name="Demo Manufacturing Site", status="active")
        s2 = Site(id=uuid.uuid4(), company_id=c2.id, name="Plant 1", status="active")
        db.add_all([s1, s2])
        await db.flush()

        p_priyanshu = Profile(
            id=uuid.uuid4(),
            email="priyanshu@gmail.com",
            full_name="Priyanshu",
            employee_id="DEMO-001",
            department="Quality Assurance",
            job_title="QA Manager",
            status="active",
        )
        p_isolated = Profile(
            id=uuid.uuid4(),
            email="isolated_user@competitor.com",
            full_name="Isolated User",
            employee_id="COMP-001",
            department="Production",
            job_title="Production User",
            status="active",
        )
        p_inactive = Profile(
            id=uuid.uuid4(),
            email="inactive@pharmaone.ai",
            full_name="Inactive User",
            status="inactive",
        )
        db.add_all([p_priyanshu, p_isolated, p_inactive])
        await db.flush()

        m_priyanshu = CompanyMembership(
            id=uuid.uuid4(),
            user_id=p_priyanshu.id,
            company_id=c1.id,
            site_id=s1.id,
            role="QA Manager",
            is_active=True,
        )
        m_isolated = CompanyMembership(
            id=uuid.uuid4(),
            user_id=p_isolated.id,
            company_id=c2.id,
            site_id=s2.id,
            role="Production User",
            is_active=True,
        )
        db.add_all([m_priyanshu, m_isolated])
        await db.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await dispose_engine()
    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Authenticated client acting as default demo user Priyanshu (Vasundha Pharma Chem Limited)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"Authorization": "Bearer test-token-priyanshu"},
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def unauthed_client() -> AsyncClient:
    """Unauthenticated client with no Authorization header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def isolated_client() -> AsyncClient:
    """Authenticated client acting as an isolated secondary company user (Competitor Pharma Limited)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"Authorization": "Bearer test-token-isolated"},
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session

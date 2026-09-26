"""Pytest fixtures and test-only configuration.

Test infrastructure is the *only* place we set configuration values inline —
application code never does. Here we populate the required environment
variables with harmless test placeholders and point the database at a local
SQLite file so the suite runs with no external services.
"""

import os
import pathlib
import sys

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
os.environ.setdefault("GROQ_MODEL", "llama-3.3-70b-versatile")
os.environ.setdefault("HUGGINGFACE_API_KEY", "test-hf-key")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.session import dispose_engine, get_engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _prepare_database():
    """Create a fresh schema for each test, then tear it down."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await dispose_engine()
    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

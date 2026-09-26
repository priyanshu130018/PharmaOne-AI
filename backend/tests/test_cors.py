"""Tests for CORS (Cross-Origin Resource Sharing) middleware and configuration.

Verifies:
- CORS middleware is active and correctly parses CORS_ORIGINS from environment.
- Preflight (OPTIONS) requests succeed for allowed origins.
- Normal GET / POST requests receive appropriate CORS response headers.
- Disallowed / untrusted origins do not receive allow headers.
- Production environment rejects wildcard ('*') origins.
- Local testing origin (http://localhost:5173) is properly supported.
"""

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.core.config import Settings


async def test_cors_preflight_allowed_origin(client: AsyncClient) -> None:
    """OPTIONS preflight request from http://localhost:5173 must return 200 and CORS headers."""
    response = await client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert "GET" in response.headers.get("access-control-allow-methods", "")


async def test_cors_get_request_allowed_origin(client: AsyncClient) -> None:
    """GET request from http://localhost:5173 receives access-control-allow-origin header."""
    response = await client.get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


async def test_cors_post_preflight_and_request(client: AsyncClient) -> None:
    """POST preflight and request from http://localhost:5173 work seamlessly."""
    # Preflight
    preflight = await client.options(
        "/api/v1/deviations/process",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers.get("access-control-allow-origin") == "http://localhost:5173"

    # Actual POST
    response = await client.post(
        "/api/v1/deviations/extract-text",
        json={"text": "Site: Plant A. Deviation in sterile filling room."},
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


async def test_cors_disallowed_origin(client: AsyncClient) -> None:
    """Requests from unlisted origins do NOT receive access-control-allow-origin."""
    response = await client.get(
        "/api/v1/health",
        headers={"Origin": "http://malicious-site.example.com"},
    )
    assert response.status_code == 200
    # Starlette CORSMiddleware does not emit access-control-allow-origin when origin is not in allow_origins
    assert "access-control-allow-origin" not in response.headers


def test_cors_settings_parsing() -> None:
    """Settings correctly parses comma-separated origins without whitespace."""
    settings = Settings(
        ENVIRONMENT="test",
        BACKEND_PORT=8000,
        API_BASE_URL="http://testserver",
        CORS_ORIGINS="http://localhost:8080, http://localhost:5173 , https://app.pharmaone.ai",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        SUPABASE_URL="https://test.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test-key",
        GROQ_API_KEY="test-key",
        GROQ_MODEL="llama-3.3-70b-versatile",
        HUGGINGFACE_API_KEY="test-key",
    )
    assert settings.cors_origins == [
        "http://localhost:8080",
        "http://localhost:5173",
        "https://app.pharmaone.ai",
    ]


def test_cors_settings_rejects_empty() -> None:
    """Empty CORS_ORIGINS is rejected with validation error."""
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="test",
            BACKEND_PORT=8000,
            API_BASE_URL="http://testserver",
            CORS_ORIGINS="   ",
            DATABASE_URL="sqlite+aiosqlite:///:memory:",
            SUPABASE_URL="https://test.supabase.co",
            SUPABASE_SERVICE_ROLE_KEY="test-key",
            GROQ_API_KEY="test-key",
            GROQ_MODEL="llama-3.3-70b-versatile",
            HUGGINGFACE_API_KEY="test-key",
        )


def test_cors_production_rejects_wildcard() -> None:
    """Wildcard '*' is strictly rejected in production environment."""
    with pytest.raises(ValidationError, match="CORS_ORIGINS cannot use wildcard"):
        Settings(
            ENVIRONMENT="production",
            BACKEND_PORT=8000,
            API_BASE_URL="https://api.pharmaone.ai",
            CORS_ORIGINS="*",
            DATABASE_URL="postgresql+asyncpg://postgres:secret@db.supabase.co:5432/postgres",
            SUPABASE_URL="https://test.supabase.co",
            SUPABASE_SERVICE_ROLE_KEY="test-key",
            GROQ_API_KEY="test-key",
            GROQ_MODEL="llama-3.3-70b-versatile",
            HUGGINGFACE_API_KEY="test-key",
        )


def test_cors_production_accepts_explicit_domains() -> None:
    """Explicit domains in production are accepted."""
    settings = Settings(
        ENVIRONMENT="production",
        BACKEND_PORT=8000,
        API_BASE_URL="https://api.pharmaone.ai",
        CORS_ORIGINS="https://your-production-frontend-domain.com,https://pharmaone.ai",
        DATABASE_URL="postgresql+asyncpg://postgres:secret@db.supabase.co:5432/postgres",
        SUPABASE_URL="https://test.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test-key",
        GROQ_API_KEY="test-key",
        GROQ_MODEL="llama-3.3-70b-versatile",
        HUGGINGFACE_API_KEY="test-key",
    )
    assert settings.cors_origins == [
        "https://your-production-frontend-domain.com",
        "https://pharmaone.ai",
    ]

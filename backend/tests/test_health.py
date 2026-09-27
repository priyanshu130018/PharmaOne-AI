from httpx import AsyncClient
from app.core.config import get_settings


async def test_health_liveness(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert "version" in body


async def test_root_health_alias(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert "version" in body
    # Verify no secrets or database credentials are leaked in response
    assert "DATABASE_URL" not in body
    assert "GROQ_API_KEY" not in body


async def test_health_readiness(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["database"] == "connected"


async def test_root(client: AsyncClient) -> None:
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json()["name"].startswith("PharmaOne AI")


async def test_unversioned_business_routes_return_404(client: AsyncClient) -> None:
    """Verify backend business routes strictly live under /api/v1 and not at unversioned root."""
    resp_deviations = await client.get("/deviations")
    assert resp_deviations.status_code == 404

    resp_reports = await client.get("/reports/summary")
    assert resp_reports.status_code == 404

    resp_extract = await client.post("/deviations/extract-text", json={"text": "test"})
    assert resp_extract.status_code == 404


async def test_versioned_business_routes_mounted(client: AsyncClient) -> None:
    """Verify backend business routes are correctly mounted under /api/v1."""
    resp_deviations = await client.get("/api/v1/deviations?limit=8")
    assert resp_deviations.status_code == 200

    resp_reports = await client.get("/api/v1/reports/summary")
    assert resp_reports.status_code == 200


def test_groq_model_configuration() -> None:
    """Verify GROQ_MODEL is configured with openai/gpt-oss-20b."""
    settings = get_settings()
    assert settings.GROQ_MODEL == "openai/gpt-oss-20b"

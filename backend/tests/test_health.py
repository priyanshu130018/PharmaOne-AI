from httpx import AsyncClient


async def test_health_liveness(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert "version" in body


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

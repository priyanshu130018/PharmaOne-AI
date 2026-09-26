from httpx import AsyncClient

SAMPLE = {
    "title": "Temperature excursion in cold storage",
    "description": "Cold room temperature exceeded 8C for 45 minutes during the night shift.",
    "deviation_type": "environmental",
    "source": "manual",
    "department": "Warehouse",
    "product_name": "ProductX",
    "product_code": "PX-100",
    "batch_number": "B-2026-001",
    "reported_by": "j.doe",
    "impact": "product_quality",
    "severity": "major",
    "assessment_reason": "Excursion outside approved storage range.",
}


async def test_create_and_get_deviation(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/deviations", json=SAMPLE)
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["reference"].startswith("DEV-")
    assert created["status"] == "submitted"
    assert created["deviation_type"] == "environmental"
    assert created["impact"] == "product_quality"
    dev_id = created["id"]

    resp = await client.get(f"/api/v1/deviations/{dev_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == dev_id


async def test_list_and_filter(client: AsyncClient) -> None:
    await client.post("/api/v1/deviations", json=SAMPLE)
    other = {**SAMPLE, "deviation_type": "equipment", "title": "Pump failure on line 3"}
    await client.post("/api/v1/deviations", json=other)

    resp = await client.get("/api/v1/deviations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2

    resp = await client.get("/api/v1/deviations", params={"deviation_type": "equipment"})
    assert resp.json()["total"] == 1


async def test_update_deviation_put(client: AsyncClient) -> None:
    dev_id = (await client.post("/api/v1/deviations", json=SAMPLE)).json()["id"]
    resp = await client.put(
        f"/api/v1/deviations/{dev_id}",
        json={"severity": "critical", "status": "under_review"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["severity"] == "critical"
    assert body["status"] == "under_review"


async def test_delete_deviation(client: AsyncClient) -> None:
    dev_id = (await client.post("/api/v1/deviations", json=SAMPLE)).json()["id"]
    assert (await client.delete(f"/api/v1/deviations/{dev_id}")).status_code == 204
    assert (await client.get(f"/api/v1/deviations/{dev_id}")).status_code == 404


async def test_reference_is_sequential(client: AsyncClient) -> None:
    first = (await client.post("/api/v1/deviations", json=SAMPLE)).json()["reference"]
    second = (await client.post("/api/v1/deviations", json=SAMPLE)).json()["reference"]
    assert first != second


async def test_validation_error_on_short_description(client: AsyncClient) -> None:
    bad = {**SAMPLE, "description": "short"}
    resp = await client.post("/api/v1/deviations", json=bad)
    assert resp.status_code == 422


async def test_reports_summary(client: AsyncClient) -> None:
    await client.post("/api/v1/deviations", json=SAMPLE)
    await client.post("/api/v1/deviations", json={**SAMPLE, "deviation_type": "equipment"})
    resp = await client.get("/api/v1/reports/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    types = {row["key"]: row["count"] for row in body["by_type"]}
    assert types.get("environmental") == 1
    assert types.get("equipment") == 1

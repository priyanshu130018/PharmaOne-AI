from httpx import AsyncClient


async def test_process_returns_extraction_and_assessment(client: AsyncClient) -> None:
    payload = {
        "content": (
            "Sterility test failure observed. Possible microbial contamination "
            "detected during testing.\nProduct: SterileInjectable\nBatch: B-2026-042"
        ),
        "source": "text",
    }
    resp = await client.post("/api/v1/deviations/process", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["is_stub"] is True
    assert body["provider"] == "stub"
    assert body["model"]
    assert body["requires_human_review"] is True

    extraction = body["extraction"]
    assert extraction["description"]
    assert extraction["batch_number"] == "B-2026-042"
    assert extraction["product_name"] == "SterileInjectable"

    assessment = body["assessment"]
    # Per compliance requirement: When Groq fails, AI severity/impact is NOT fabricated.
    # Instead, recommended_severity and recommended_impact are None (unassigned),
    # leaving final classification to human review with clear notice of service disruption.
    assert assessment["recommended_severity"] is None
    assert assessment["recommended_impact"] is None
    assert "unavailable due to AI service disruption" in assessment["reason"]
    assert assessment["criteria_note"]
    assert isinstance(assessment["evidence"], list)


async def test_process_equipment_minor(client: AsyncClient) -> None:
    payload = {"content": "The mixing pump on line 2 made an unusual noise but kept running."}
    resp = await client.post("/api/v1/deviations/process", json=payload)
    body = resp.json()
    assert body["extraction"]["deviation_type"] == "equipment"
    assert body["assessment"]["recommended_severity"] is None
    assert "unavailable" in body["assessment"]["reason"].lower()


async def test_process_rejects_empty_content(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/deviations/process", json={"content": "x"})
    assert resp.status_code == 422


async def test_process_then_save_flow(client: AsyncClient) -> None:
    """End-to-end: process content, then save a reviewed deviation carrying
    the AI snapshots (the documented human-in-the-loop flow)."""
    proc = (
        await client.post(
            "/api/v1/deviations/process",
            json={"content": "OOS result on assay for batch B-9. Impurity above limit."},
        )
    ).json()

    save_payload = {
        "title": proc["extraction"]["title"] or "OOS assay result",
        "description": proc["extraction"]["description"],
        "deviation_type": proc["extraction"]["deviation_type"] or "laboratory",
        "severity": "major",  # Human reviewer provides authoritative severity
        "impact": "product_quality",
        "assessment_reason": "Human reviewer evaluated OOS result and confirmed major product quality impact.",
        "ai_extraction": proc["extraction"],
        "ai_assessment": proc["assessment"],
    }
    resp = await client.post("/api/v1/deviations", json=save_payload)
    assert resp.status_code == 201, resp.text
    saved = resp.json()
    assert saved["severity"] == "major"
    assert saved["ai_assessment"]["recommended_severity"] == proc["assessment"]["recommended_severity"]

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


async def test_human_review_override_persistence(client: AsyncClient) -> None:
    """Verifies that human edits take precedence over AI recommendations while AI
    recommendations are preserved for regulatory traceability."""
    payload = {
        "title": "Sterilizer temperature excursion during cycle 4",
        "description": "Temperature dipped 1.5C below setpoint for 90 seconds during hold phase.",
        "deviation_type": "equipment",
        "source": "manual",
        "site_plant": "Plant 1 - Sterile Vial Line",
        "product_name": "Vaccine-Adjuvant B",
        "batch_number": "VAC-2026-09",
        # User reviews and overrides AI: sets Minor instead of AI's Critical recommendation
        "severity": "minor",
        "impact": "compliance",
        "assessment_reason": "Engineering confirmed redundant heating element engaged within tolerance limits.",
        # AI snapshot from intake analysis:
        "ai_assessment": {
            "severity": "critical",
            "impact": "patient_safety",
            "reason": "AI initial assessment flagged potential non-sterility risk.",
            "evidence": ["SOP-AUT-001 Section 4.3"],
        },
    }

    resp = await client.post("/api/v1/deviations", json=payload)
    assert resp.status_code == 201, resp.text
    saved = resp.json()

    # Authoritative user-reviewed values are persisted as final
    assert saved["severity"] == "minor"
    assert saved["impact"] == "compliance"
    assert "redundant heating element" in saved["assessment_reason"]

    # AI recommendations are preserved for audit trail
    assert saved["ai_recommended_severity"] == "critical"
    assert saved["ai_recommended_impact"] == "patient_safety"
    assert "AI initial assessment" in saved["ai_reason"]
    assert "SOP-AUT-001 Section 4.3" in saved["ai_evidence"]
    assert saved["success"] is True

    # Confirm persistence by re-fetching from database
    dev_id = saved["id"]
    get_resp = await client.get(f"/api/v1/deviations/{dev_id}")
    assert get_resp.status_code == 200
    persisted = get_resp.json()
    assert persisted["severity"] == "minor"
    assert persisted["ai_recommended_severity"] == "critical"


async def test_aivoa_canonical_fields_storage(client: AsyncClient) -> None:
    """Verifies that canonical AIVOA Log Deviation form fields are accepted,
    persisted in database, and returned in DeviationRead."""
    payload = {
        "site_plant": "Building 4 - Injectables",
        "date_of_occurrence": "2026-03-15",
        "title_short_description": "Autoclave cycle temperature drop",
        "detailed_description": "Autoclave cycle 12 dropped below 121C for 3 minutes before recovering.",
        "related_product_material": "Sterile Saline 0.9%",
        "batch_lot_number": "LOT-99214",
        "deviation_type": "equipment",
        "parameter": "Sterilization Chamber Temperature",
        "approved_range": "121.0 - 124.0 C",
        "actual_value": "119.5 C",
        "duration": "3 minutes",
        "immediate_action": "Cycle halted and QA supervisor notified immediately.",
        "qa_notified": True,
        "initial_impact": "product_quality",
        "initial_severity": "major",
    }

    resp = await client.post("/api/v1/deviations", json=payload)
    assert resp.status_code == 201, resp.text
    saved = resp.json()

    assert saved["site_plant"] == "Building 4 - Injectables"
    assert saved["date_of_occurrence"] == "2026-03-15"
    assert saved["title_short_description"] == "Autoclave cycle temperature drop"
    assert saved["title"] == "Autoclave cycle temperature drop"
    assert saved["detailed_description"] == "Autoclave cycle 12 dropped below 121C for 3 minutes before recovering."
    assert saved["description"] == "Autoclave cycle 12 dropped below 121C for 3 minutes before recovering."
    assert saved["related_product_material"] == "Sterile Saline 0.9%"
    assert saved["batch_lot_number"] == "LOT-99214"
    assert saved["parameter"] == "Sterilization Chamber Temperature"
    assert saved["approved_range"] == "121.0 - 124.0 C"
    assert saved["actual_value"] == "119.5 C"
    assert saved["duration"] == "3 minutes"
    assert saved["immediate_action"] == "Cycle halted and QA supervisor notified immediately."
    assert saved["qa_notified"] is True
    assert saved["initial_impact"] == "product_quality"
    assert saved["impact"] == "product_quality"
    assert saved["initial_severity"] == "major"
    assert saved["severity"] == "major"
    assert saved["success"] is True


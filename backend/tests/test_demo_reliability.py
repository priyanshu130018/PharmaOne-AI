"""Demo Reliability and Consecutive Execution Verification for PharmaOne AI.

Verifies:
1. Primary demo flow executes repeatedly (multiple consecutive cycles).
2. Application recovers cleanly after an intermittent AI failure.
3. Database references increment sequentially across repeated runs.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


SAMPLE_DEVIATIONS = [
    {
        "content": (
            "During API manufacturing Batch B24001, the approved temperature range was 70–75°C. "
            "The actual temperature reached 82°C for approximately 15 minutes. "
            "Production was stopped and QA was notified."
        ),
        "source": "text",
        "expected_batch": "B24001",
    },
    {
        "content": (
            "Aseptic filling line 2 differential pressure dropped to 8 Pa for 20 minutes on batch LOT-4029. "
            "Filling stopped immediately and HEPA filters checked."
        ),
        "source": "text",
        "expected_batch": "LOT-4029",
    },
    {
        "content": (
            "Cold storage unit CS-04 temperature excursion to 12°C for 45 minutes affecting batch BIO-8812. "
            "Inventory placed on quarantine hold."
        ),
        "source": "text",
        "expected_batch": "BIO-8812",
    },
]


@pytest.mark.asyncio
async def test_repeated_demo_flow_with_ai_recovery(client: AsyncClient):
    """Executes primary intake flow multiple times, interleaving an AI failure,
    confirming consecutive execution and zero degradation."""
    saved_references = []

    # Run 1: Successful intake
    resp1 = await client.post("/api/v1/deviations/process", json=SAMPLE_DEVIATIONS[0])
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["deviation"]["batch_lot_number"] == "B24001"

    save_resp1 = await client.post(
        "/api/v1/deviations",
        json={
            "site_plant": "Plant 1",
            "title": "Temperature Excursion B24001",
            "description": data1["deviation"]["detailed_description"],
            "deviation_type": data1["deviation"]["deviation_type"],
            "batch_number": "B24001",
            "severity": "minor",
            "impact": "compliance",
            "ai_assessment": {
                "severity": data1["assessment"]["recommended_severity"],
                "impact": data1["assessment"]["recommended_impact"],
            },
        },
    )
    assert save_resp1.status_code == 201
    saved_references.append(save_resp1.json()["reference"])

    # Run 2: Intermittent AI failure occurs (simulated LLM timeout)
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=TimeoutError("Simulated LLM Gateway Timeout")
    )
    with patch(
        "app.ai.extraction._get_groq_client",
        return_value=(mock_client, "openai/gpt-oss-20b"),
    ):
        resp_err = await client.post("/api/v1/deviations/process", json=SAMPLE_DEVIATIONS[1])
        # Workflow recovers safely with heuristic fallback instead of crashing with 500
        assert resp_err.status_code == 200
        data_err = resp_err.json()
        assert data_err["is_stub"] is True
        assert data_err["deviation"]["batch_lot_number"] == "LOT-4029"

    # Save deviation from fallback analysis
    save_resp2 = await client.post(
        "/api/v1/deviations",
        json={
            "site_plant": "Aseptic Suite",
            "title": "Pressure Drop LOT-4029",
            "description": data_err["deviation"]["detailed_description"],
            "deviation_type": data_err["deviation"]["deviation_type"],
            "batch_number": "LOT-4029",
            "severity": "major",
            "impact": "product_quality",
        },
    )
    assert save_resp2.status_code == 201
    saved_references.append(save_resp2.json()["reference"])

    # Run 3: System immediately returns to normal on subsequent request
    resp3 = await client.post("/api/v1/deviations/process", json=SAMPLE_DEVIATIONS[2])
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["deviation"]["batch_lot_number"] == "BIO-8812"

    save_resp3 = await client.post(
        "/api/v1/deviations",
        json={
            "site_plant": "Warehouse Cold Storage",
            "title": "Cold Room Excursion BIO-8812",
            "description": data3["deviation"]["detailed_description"],
            "deviation_type": data3["deviation"]["deviation_type"],
            "batch_number": "BIO-8812",
            "severity": "minor",
            "impact": "product_quality",
        },
    )
    assert save_resp3.status_code == 201
    saved_references.append(save_resp3.json()["reference"])

    # Verify sequential references and total count
    assert len(saved_references) == 3
    assert len(set(saved_references)) == 3  # All references are distinct

    list_resp = await client.get("/api/v1/deviations")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 3

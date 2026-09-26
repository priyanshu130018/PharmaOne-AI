"""End-to-End Integration and Reliability Verification for PharmaOne AI.

Tests the complete chain specified in the user request:
1. Representative deviation input:
   "During API manufacturing Batch B24001, the approved temperature range was 70–75°C.
    The actual temperature reached 82°C for approximately 15 minutes.
    Production was stopped and QA was notified."
2. PDF/Text Extraction (POST /api/v1/deviations/extract-text)
3. Structured AI Extraction & LangGraph Workflow (POST /api/v1/deviations/process)
4. Vector RAG Reference Retrieval and SOP Citations
5. Initial Impact & Severity Assessments
6. Human Review / Override:
   AI recommends Critical/Major -> User reviews and sets Minor
7. Persistence (POST /api/v1/deviations)
8. Database Record Query & Verification (GET /api/v1/deviations/{id}):
   - Authoritative user value: severity = 'minor'
   - AI audit snapshot: ai_recommended_severity = 'major' / 'critical'
9. Database resilience & constraint tests:
   - Database unavailable handling
   - Duplicate reference sequential integrity
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from unittest.mock import patch

from app.core.enums import DeviationStatus, Severity
from app.models.deviation import Deviation
from app.db.session import get_sessionmaker


REPRESENTATIVE_DEVIATION_TEXT = (
    "During API manufacturing Batch B24001, the approved temperature range was 70–75°C. "
    "The actual temperature reached 82°C for approximately 15 minutes. "
    "Production was stopped and QA was notified."
)


@pytest.mark.asyncio
async def test_complete_end_to_end_pipeline(client: AsyncClient):
    """Executes the complete, unbroken end-to-end chain from raw input to DB verification."""

    # --------------------------------------------------------------------------
    # Step 1 & 2: Document / Text Extraction
    # --------------------------------------------------------------------------
    extract_resp = await client.post(
        "/api/v1/deviations/extract-text",
        json={"text": REPRESENTATIVE_DEVIATION_TEXT, "source_type": "text"},
    )
    assert extract_resp.status_code == 200, extract_resp.text
    extract_data = extract_resp.json()
    assert extract_data["success"] is True
    normalized_text = extract_data["extracted_text"]
    assert "Batch B24001" in normalized_text
    assert "82°C" in normalized_text or "82" in normalized_text

    # --------------------------------------------------------------------------
    # Step 3, 4, 5: AI Structured Extraction, Vector RAG & Risk Assessment
    # --------------------------------------------------------------------------
    process_resp = await client.post(
        "/api/v1/deviations/process",
        json={"content": normalized_text, "source": "text"},
    )
    assert process_resp.status_code == 200, process_resp.text
    process_data = process_resp.json()

    # Structured deviation verification
    dev = process_data["deviation"]
    assert dev["batch_lot_number"] == "B24001"
    assert dev["deviation_type"] in ("equipment", "process", "environmental", "material", "other")
    assert dev["qa_notified"] is True

    # RAG Reference Retrieval verification
    assert process_data["rag_available"] is True
    sources = process_data["retrieved_sources"]
    assert len(sources) > 0
    # Temperature/calibration/reactor SOP should be retrieved
    assert any("temperature" in s["content"].lower() or "sop" in s["document_name"].lower() for s in sources)

    # Initial AI Assessment
    assessment = process_data["assessment"]
    ai_rec_severity = assessment["recommended_severity"]
    ai_rec_impact = assessment["recommended_impact"]
    assert ai_rec_severity in ("minor", "major", "critical")
    assert assessment["criteria_note"]
    assert len(assessment["evidence"]) > 0
    assert process_data["requires_human_review"] is True

    # --------------------------------------------------------------------------
    # Step 6: Human Review / Edit (User is authoritative)
    # The user reviews the AI output. Suppose AI recommended 'major' or 'critical'.
    # The user consults engineering logs and decides the actual severity is 'minor'.
    # --------------------------------------------------------------------------
    user_final_severity = "minor"
    user_final_impact = "compliance"
    user_rationale = (
        "Human Reviewer Override: Engineering analysis verified product thermal stability "
        "was not degraded during the 15-minute excursion. Redundant secondary sensor confirmed "
        "mass temperature remained below degradation threshold."
    )

    save_payload = {
        "site_plant": "API Synthesis Facility - Reactor Line 2",
        "date_of_occurrence": "2026-03-22",
        "title_short_description": "Temperature excursion in API manufacturing Batch B24001",
        "detailed_description": dev["detailed_description"],
        "source": "text",
        "related_product_material": dev.get("related_product_material") or "API Bulk Compound",
        "batch_lot_number": dev["batch_lot_number"],
        "deviation_type": dev["deviation_type"],
        "parameter": dev.get("parameter") or "Reactor Temperature",
        "approved_range": dev.get("approved_range") or "70–75°C",
        "actual_value": dev.get("actual_value") or "82°C",
        "duration": dev.get("duration") or "15 minutes",
        "immediate_action": dev.get("immediate_action") or "Production stopped and QA notified.",
        "qa_notified": True,
        # Human-reviewed authoritative values:
        "severity": user_final_severity,
        "impact": user_final_impact,
        "assessment_reason": user_rationale,
        # Original AI snapshot for regulatory traceability:
        "ai_assessment": {
            "severity": ai_rec_severity,
            "impact": ai_rec_impact,
            "reason": assessment["reason"],
            "evidence": assessment["evidence"],
        },
    }

    # --------------------------------------------------------------------------
    # Step 7: Persistence to Database
    # --------------------------------------------------------------------------
    create_resp = await client.post("/api/v1/deviations", json=save_payload)
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["success"] is True
    dev_id = created["id"]
    reference = created["reference"]
    assert reference.startswith("DEV-")

    # --------------------------------------------------------------------------
    # Step 8: Database Query & Verification of Final Stored Values
    # --------------------------------------------------------------------------
    fetch_resp = await client.get(f"/api/v1/deviations/{dev_id}")
    assert fetch_resp.status_code == 200, fetch_resp.text
    stored = fetch_resp.json()

    # The official stored severity must be the human's choice
    assert stored["severity"] == user_final_severity
    assert stored["impact"] == user_final_impact
    assert user_rationale in stored["assessment_reason"]

    # The AI's original recommendation must remain separately identifiable
    assert stored["ai_recommended_severity"] == ai_rec_severity
    assert stored["ai_recommended_impact"] == ai_rec_impact
    assert stored["batch_lot_number"] == "B24001"
    assert stored["qa_notified"] is True
    assert stored["site_plant"] == "API Synthesis Facility - Reactor Line 2"
    assert stored["status"] == "submitted"


@pytest.mark.asyncio
async def test_database_duplicate_reference_protection():
    """Verify that the database enforces unique references and cannot store duplicate keys."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        # Create first record
        dev1 = Deviation(
            reference="DEV-UNIQUE-001",
            title="First deviation",
            description="Detailed description for first deviation entry.",
            deviation_type="equipment",
            status=DeviationStatus.SUBMITTED,
        )
        session.add(dev1)
        await session.commit()

        # Attempt to insert identical reference
        dev2 = Deviation(
            reference="DEV-UNIQUE-001",
            title="Duplicate deviation",
            description="Detailed description for duplicate deviation entry.",
            deviation_type="equipment",
            status=DeviationStatus.SUBMITTED,
        )
        session.add(dev2)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_database_unavailable_health_reporting(client: AsyncClient):
    """Verify readiness probe correctly flags degraded status when database is unreachable."""
    with patch("app.api.v1.health.get_sessionmaker", side_effect=ConnectionRefusedError("Database host unreachable")):
        resp = await client.get("/api/v1/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["database"] == "unavailable"

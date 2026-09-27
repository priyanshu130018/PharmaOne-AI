"""Unit tests for the LangGraph AI Deviation Intake workflow, Groq extraction,
Pydantic schema validation, and Vector RAG reference retrieval.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.enums import DeviationSource, Impact, Severity
from app.schemas.process import (
    AssessmentResult,
    ProcessResponse,
    RetrievedSource,
    StructuredDeviation,
)
from app.ai import (
    DeviationWorkflowState,
    _heuristic_fallback_extraction,
    assess_impact_node,
    assess_severity_node,
    create_deviation_intake_graph,
    deviation_graph,
    extract_deviation_node,
    prepare_final_assessment_node,
    process_deviation,
    retrieve_reference_context_node,
    validate_input_node,
    validate_structured_output_node,
)
from app.rag.service import RagService


# ==============================================================================
# 1. Valid Structured Extraction with Groq
# ==============================================================================


@pytest.mark.asyncio
async def test_valid_structured_extraction():
    """Verify that valid LLM output is correctly parsed into StructuredDeviation."""
    mock_extracted_json = {
        "site_plant": "Sterile Fill-Finish Facility 1",
        "date_of_occurrence": "2026-03-20T14:15:00Z",
        "title_short_description": "Autoclave Sterilization Exposure Temperature Drop",
        "source": "text",
        "related_product_material": "Sterile Saline Injection 100mL",
        "batch_lot_number": "LOT-2026-991",
        "detailed_description": "During terminal sterilization, autoclave AC-02 dropped to 119.5C for 6 minutes.",
        "deviation_type": "equipment",
        "manufacturing_stage": "Terminal Sterilization",
        "equipment": "Autoclave AC-02",
        "department": "Sterile Production",
        "parameter": "Chamber Temperature",
        "approved_range": "121.1C +/- 0.5C",
        "actual_value": "119.5C",
        "duration": "6 minutes",
        "immediate_action": "Sterilization cycle aborted and autoclave load quarantined under tag Q-882.",
        "qa_notified": True,
        "extracted_facts": [
            "Autoclave AC-02 temperature dropped to 119.5C",
            "Hold phase was 6 minutes below validated 120.5C limit",
            "Load quarantined under tag Q-882",
        ],
        "inferred_information": [
            "Sterility Assurance Level (SAL) 10^-6 could not be guaranteed for the batch"
        ],
        "missing_information": [],
    }

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(mock_extracted_json)
    mock_response = MagicMock(choices=[mock_choice])
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch("app.ai.extraction._get_groq_client", return_value=(mock_client, "openai/gpt-oss-20b")):
        state: DeviationWorkflowState = {
            "raw_content": "Autoclave AC-02 dropped to 119.5C for 6 minutes on batch LOT-2026-991.",
            "source": "text",
            "is_valid": True,
        }
        res = await extract_deviation_node(state)

        assert res["is_stub"] is False
        assert res["provider"] == "groq"
        assert res["raw_extraction_output"]["batch_lot_number"] == "LOT-2026-991"
        assert res["raw_extraction_output"]["parameter"] == "Chamber Temperature"

        # Validate structured node
        val_state: DeviationWorkflowState = {
            "is_valid": True,
            "raw_extraction_output": res["raw_extraction_output"],
        }
        val_res = await validate_structured_output_node(val_state)
        dev = val_res["structured_deviation"]

        assert dev["site_plant"] == "Sterile Fill-Finish Facility 1"
        assert dev["actual_value"] == "119.5C"
        assert dev["approved_range"] == "121.1C +/- 0.5C"
        assert len(dev["extracted_facts"]) == 3
        assert len(dev["inferred_information"]) == 1
        assert dev["missing_information"] == []


# ==============================================================================
# 2. Missing Fields Handling (Null values and cataloged in missing_information)
# ==============================================================================


@pytest.mark.asyncio
async def test_missing_fields_handling():
    """Verify that when facts are missing, fields remain null and are listed in missing_information."""
    mock_sparse_json = {
        "site_plant": None,
        "date_of_occurrence": None,
        "title_short_description": "Mixing pump vibration in buffer prep",
        "source": "text",
        "related_product_material": None,
        "batch_lot_number": None,
        "detailed_description": "The mixing pump made an unusual sound during buffer staging.",
        "deviation_type": "equipment",
        "manufacturing_stage": "Buffer Preparation",
        "equipment": "Mixing Pump MP-1",
        "department": None,
        "parameter": None,
        "approved_range": None,
        "actual_value": None,
        "duration": None,
        "immediate_action": "Operator paused pump and called maintenance.",
        "qa_notified": False,
        "extracted_facts": ["Mixing pump made an unusual sound"],
        "inferred_information": [],
        "missing_information": [
            "batch_lot_number",
            "approved_range",
            "actual_value",
            "date_of_occurrence",
            "department",
            "parameter",
            "duration",
        ],
    }

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(mock_sparse_json)
    mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(choices=[mock_choice]))

    with patch("app.ai.extraction._get_groq_client", return_value=(mock_client, "openai/gpt-oss-20b")):
        state: DeviationWorkflowState = {
            "raw_content": "The mixing pump made an unusual sound during buffer staging.",
            "source": "text",
            "is_valid": True,
        }
        ext_res = await extract_deviation_node(state)
        val_res = await validate_structured_output_node({
            "is_valid": True,
            "raw_extraction_output": ext_res["raw_extraction_output"],
        })
        dev = val_res["structured_deviation"]

        # Missing fields must remain None / null, not hallucinated
        assert dev["batch_lot_number"] is None
        assert dev["date_of_occurrence"] is None
        assert dev["approved_range"] is None
        assert dev["actual_value"] is None
        assert dev["site_plant"] is None
        assert "batch_lot_number" in dev["missing_information"]
        assert "approved_range" in dev["missing_information"]


# ==============================================================================
# 3. Invalid / Malformed LLM Output Safe Fallback
# ==============================================================================


@pytest.mark.asyncio
async def test_invalid_llm_output_malformed_json():
    """Verify that unparseable or malformed LLM output triggers fallback without crashing."""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    # Invalid JSON that json.loads will fail on
    mock_choice.message.content = "Here is the result: { invalid_json : true, missing quotes "
    mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(choices=[mock_choice]))

    with patch("app.ai.extraction._get_groq_client", return_value=(mock_client, "openai/gpt-oss-20b")):
        state: DeviationWorkflowState = {
            "raw_content": "Batch B-999 had a temperature excursion in the cold room.",
            "source": "text",
            "is_valid": True,
        }
        res = await extract_deviation_node(state)

        # Must not crash; should fall back safely to heuristic extraction
        assert res["is_stub"] is True
        assert res["provider"] == "stub"
        assert res["raw_extraction_output"]["batch_lot_number"] == "B-999"

        # Pydantic validation must successfully handle the fallback output
        val_res = await validate_structured_output_node({
            "is_valid": True,
            "raw_extraction_output": res["raw_extraction_output"],
        })
        assert val_res["structured_deviation"]["batch_lot_number"] == "B-999"


# ==============================================================================
# 4. LLM Timeout or API Failure Handling
# ==============================================================================


@pytest.mark.asyncio
async def test_llm_timeout_and_failure():
    """Verify that an LLM timeout or connection failure falls back gracefully."""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=TimeoutError("Groq gateway connection timed out"))

    with patch("app.ai.extraction._get_groq_client", return_value=(mock_client, "openai/gpt-oss-20b")):
        state: DeviationWorkflowState = {
            "raw_content": "Sterility test failure observed in batch B-440.",
            "source": "text",
            "is_valid": True,
        }
        res = await extract_deviation_node(state)

        assert res["is_stub"] is True
        assert res["provider"] == "stub"
        assert "LLM extraction error" in res["extraction_error"]
        assert res["raw_extraction_output"]["batch_lot_number"] == "B-440"


# ==============================================================================
# 5. RAG Success: Retrieved Chunks with Full Metadata
# ==============================================================================


def test_rag_service_retrieves_chunks_with_metadata():
    """Verify RagService retrieves top-k relevant chunks with full metadata."""
    rag = RagService.get_instance()
    query = "Autoclave temperature sterilization hold below 120.5C cycle aborted"
    chunks, success, error_msg = rag.retrieve(query=query, top_k=3, min_similarity=0.08)

    assert success is True
    assert error_msg is None
    assert len(chunks) > 0
    assert len(chunks) <= 3

    top_chunk = chunks[0]
    assert "document_name" in top_chunk
    assert "chunk_id" in top_chunk
    assert "section" in top_chunk
    assert "similarity_score" in top_chunk
    assert "content" in top_chunk
    assert top_chunk["similarity_score"] > 0.08
    assert "SOP-PR-108" in top_chunk["document_name"]


@pytest.mark.asyncio
async def test_rag_node_success():
    """Verify retrieve_reference_context_node populates retrieved_chunks."""
    state: DeviationWorkflowState = {
        "is_valid": True,
        "structured_deviation": {
            "detailed_description": "Cleanroom Grade A microbial count excursion in filling suite.",
            "parameter": "viable count",
            "equipment": "Filling Line 1",
            "deviation_type": "environmental",
        },
    }
    res = await retrieve_reference_context_node(state)

    assert res["rag_available"] is True
    assert len(res["retrieved_chunks"]) > 0
    # Cleanroom excursion should match SOP-QA-042
    doc_names = [c["document_name"] for c in res["retrieved_chunks"]]
    assert any("SOP-QA-042" in name for name in doc_names)


# ==============================================================================
# 6. RAG Failure Handled Gracefully (No crash, application continues)
# ==============================================================================


@pytest.mark.asyncio
async def test_rag_failure_handled_gracefully():
    """Verify that an unexpected exception in RAG retrieval doesn't crash the workflow."""
    with patch.object(RagService, "retrieve", side_effect=RuntimeError("Vector index corrupted or unreachable")):
        state: DeviationWorkflowState = {
            "is_valid": True,
            "structured_deviation": {
                "detailed_description": "Sterility failure in lot B-101",
            },
        }
        res = await retrieve_reference_context_node(state)

        # Must catch exception and continue safely without pretending evidence was found
        assert res["rag_available"] is False
        assert res["retrieved_chunks"] == []
        assert "RAG retrieval unavailable" in res["rag_notes"]


# ==============================================================================
# 7. No Relevant Documents (Low similarity query yields empty chunks safely)
# ==============================================================================


def test_rag_no_relevant_documents_low_similarity():
    """Verify that an out-of-domain query returns empty list without error."""
    rag = RagService.get_instance()
    query = "quantum teleportation black hole singularity galactic astrophysics 99999"
    chunks, success, msg = rag.retrieve(query=query, top_k=3, min_similarity=0.20)

    assert success is True
    assert chunks == []


# ==============================================================================
# 8. Full LangGraph State Transitions & Graph Invocation
# ==============================================================================


@pytest.mark.asyncio
async def test_final_langgraph_state_flow():
    """Verify full end-to-end execution flow through compiled deviation_graph."""
    initial_state: DeviationWorkflowState = {
        "raw_content": (
            "Cold room storage excursion detected for batch LOT-501.\n"
            "Temperature reached 14.5C for 2.5 hours. Product: BioVaccine.\n"
            "Action: Quarantine initiated by QA."
        ),
        "source": "text",
        "is_valid": True,
        "retrieved_chunks": [],
        "rag_available": True,
    }

    final_state = await deviation_graph.ainvoke(initial_state)

    assert final_state["is_valid"] is True
    assert "structured_deviation" in final_state
    assert "retrieved_chunks" in final_state
    assert "impact_assessment" in final_state
    assert "severity_assessment" in final_state
    assert "final_response" in final_state

    resp_data = final_state["final_response"]
    resp = ProcessResponse.model_validate(resp_data)

    assert resp.deviation.batch_lot_number == "LOT-501"
    assert resp.requires_human_review is True
    assert resp.assessment.recommended_severity is None or resp.assessment.recommended_severity in (
        Severity.MINOR,
        Severity.MAJOR,
        Severity.CRITICAL,
    )
    assert resp.assessment.criteria_note


# ==============================================================================
# 9. Short / Invalid Input Rejected Safely in Graph
# ==============================================================================


@pytest.mark.asyncio
async def test_validation_node_rejects_too_short_input():
    """Verify validate_input_node catches short input and short-circuits graph."""
    state: DeviationWorkflowState = {"raw_content": "bad"}
    val_res = await validate_input_node(state)

    assert val_res["is_valid"] is False
    assert val_res["validation_error"] is not None

    # Verify prepare_final_assessment_node generates valid error response
    err_state: DeviationWorkflowState = {
        "is_valid": False,
        "raw_content": "bad",
        "validation_error": val_res["validation_error"],
    }
    final_res = await prepare_final_assessment_node(err_state)
    assert final_res["final_response"]["error"] == val_res["validation_error"]


# ==============================================================================
# 10. Quality Risk Context Decoupled from Severity Recommendation
# ==============================================================================


@pytest.mark.asyncio
async def test_impact_and_severity_decoupling():
    """Verify assess_impact evaluates CQAs/risk factors while assess_severity evaluates severity."""
    dev_data = {
        "detailed_description": "Cleanroom Grade A viable count exceeded limit.",
        "deviation_type": "environmental",
        "title_short_description": "Cleanroom excursion",
        "missing_information": [],
    }
    chunks = [
        {
            "document_name": "SOP-QA-042",
            "chunk_id": "C1",
            "section": "Cleanroom Action Limits",
            "page_or_chunk": "P1",
            "similarity_score": 0.85,
            "content": "Viable count excursion triggers line hold.",
        }
    ]

    # Node 5: assess_impact evaluates quality impact only
    impact_res = await assess_impact_node({
        "is_valid": True,
        "structured_deviation": dev_data,
        "retrieved_chunks": chunks,
    })
    impact = impact_res["impact_assessment"]
    assert "potential_product_impact" in impact or "risk_factors" in impact
    # assess_impact does NOT determine recommended_severity
    assert "recommended_severity" not in impact

    # Node 6: assess_severity recommends initial severity based on quality-risk context
    sev_res = await assess_severity_node({
        "is_valid": True,
        "structured_deviation": dev_data,
        "impact_assessment": impact,
        "retrieved_chunks": chunks,
    })
    sev = sev_res["severity_assessment"]
    assert sev["recommended_severity"] is None or sev["recommended_severity"] in ("minor", "major", "critical")
    assert sev["recommended_impact"] is None or sev["recommended_impact"] in (
        "patient_safety",
        "product_quality",
        "regulatory_compliance",
        "data_integrity",
        "none",
    )


# ==============================================================================
# 11. End-to-End API Integration via /api/v1/deviations/process
# ==============================================================================


@pytest.mark.asyncio
async def test_process_endpoint_returns_rich_rag_response(client: AsyncClient):
    """Verify /api/v1/deviations/process returns complete structured deviation and RAG sources."""
    payload = {
        "content": (
            "During terminal sterilization of batch B-778 in Autoclave AC-01, "
            "chamber temperature dropped to 118C for 5 minutes. The cycle was aborted "
            "and all trays quarantined."
        ),
        "source": "text",
    }
    resp = await client.post("/api/v1/deviations/process", json=payload)
    assert resp.status_code == 200
    body = resp.json()

    # Verify structured deviation schema
    assert "deviation" in body
    dev = body["deviation"]
    assert dev["batch_lot_number"] == "B-778"
    assert isinstance(dev["extracted_facts"], list)
    assert isinstance(dev["missing_information"], list)

    # Verify RAG retrieved sources
    assert "retrieved_sources" in body
    assert body["rag_available"] is True
    sources = body["retrieved_sources"]
    assert len(sources) > 0
    assert any("SOP-PR-108" in s["document_name"] for s in sources)

    # Verify AssessmentResult
    assert "assessment" in body
    assessment = body["assessment"]
    assert assessment["recommended_severity"] is None or assessment["recommended_severity"] in ("minor", "major", "critical")
    assert assessment["criteria_note"]
    assert isinstance(assessment["evidence"], list)

    # Verify human review disclaimer
    assert body["requires_human_review"] is True


@pytest.mark.asyncio
async def test_groq_unavailable_and_connection_refused_fallback():
    """Verify that when Groq service is unavailable (e.g. 503 or ConnectionRefused),
    the workflow seamlessly degrades to heuristic extraction with clear error notes."""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=ConnectionRefusedError("Connection to Groq API endpoint refused (503 Service Unavailable)")
    )

    with patch("app.ai.extraction._get_groq_client", return_value=(mock_client, "openai/gpt-oss-20b")):
        state: DeviationWorkflowState = {
            "raw_content": "Batch LOT-909 experienced pressure spike of 4.2 bar in filtration unit.",
            "source": "text",
            "is_valid": True,
        }
        res = await extract_deviation_node(state)
        assert res["is_stub"] is True
        assert res["provider"] == "stub"
        assert "LLM extraction error" in res["extraction_error"]
        assert res["raw_extraction_output"]["batch_lot_number"] == "LOT-909"


@pytest.mark.asyncio
async def test_rag_embedding_calculation_error_fallback():
    """Verify that if vector calculation/similarity comparison encounters an unexpected error,
    the workflow logs the issue, sets rag_available=False, and proceeds without crashing."""
    with patch.object(RagService, "retrieve", side_effect=RuntimeError("Vector embedding math failure")):
        state: DeviationWorkflowState = {
            "is_valid": True,
            "structured_deviation": {
                "detailed_description": "Excursion during autoclave run",
                "deviation_type": "equipment",
            },
        }
        res = await retrieve_reference_context_node(state)
        assert res["rag_available"] is False
        assert res["retrieved_chunks"] == []
        assert "RAG retrieval unavailable" in res["rag_notes"]

"""Risk assessment and final response compilation nodes for AI Deviation Intake."""

from __future__ import annotations

import json
from typing import Any

from app.ai.extraction import _get_groq_client
from app.ai.models import DeviationWorkflowState
from app.ai.prompts import (
    CRITERIA_NOTE,
    IMPACT_ASSESSMENT_SYSTEM_PROMPT,
    SEVERITY_ASSESSMENT_SYSTEM_PROMPT,
)
from app.core.config import get_settings
from app.core.enums import (
    BatchStatus,
    Impact,
    Severity,
)
from app.core.logging import get_logger
from app.schemas.process import (
    AssessmentResult,
    ExtractionResult,
    ProcessResponse,
    RetrievedSource,
    StructuredDeviation,
)

logger = get_logger("pharmaone.ai_risk_assessment")


async def assess_impact_node(state: DeviationWorkflowState) -> dict[str, Any]:
    """Node 5: Quality-risk context generation.

    Analyzes product/process impact and CQAs using retrieved SOPs.
    Strictly does NOT assign regulatory severity (matches n8n separation).
    """
    if not state.get("is_valid", True):
        return {}

    dev = state.get("structured_deviation") or {}
    chunks = state.get("retrieved_chunks") or []
    logger.info("Node [assess_impact]: evaluating quality-risk context with %d reference chunks", len(chunks))

    ref_text = "\n\n".join(
        f"[{c['document_name']} - {c['section']}]:\n{c['content']}" for c in chunks
    ) if chunks else "No reference SOPs were available for this evaluation."

    user_prompt = (
        f"Deviation Details:\n{json.dumps(dev, indent=2)}\n\n"
        f"Retrieved Reference Context:\n{ref_text}"
    )

    try:
        client, model = _get_groq_client()
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": IMPACT_ASSESSMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=2048,
        )
        impact_json = json.loads(response.choices[0].message.content or "{}")
        return {"impact_assessment": impact_json}
    except Exception as exc:
        logger.warning("Node [assess_impact]: LLM impact assessment call failed (%s). Using safe unverified state.", exc)
        return {
            "impact_assessment": {
                "risk_factors": [],
                "potential_product_impact": (
                    "Quality impact assessment unavailable due to AI service disruption. "
                    "Requires manual review by authorized quality personnel."
                ),
                "quality_risk_considerations": ["Manual evaluation of Critical Quality Attributes required."],
                "uncertainties": dev.get("missing_information", []) + ["AI evaluation disrupted"],
            }
        }


async def assess_severity_node(state: DeviationWorkflowState) -> dict[str, Any]:
    """Node 6: Initial AI severity recommendation based on deviation information and retrieved quality-risk context."""
    if not state.get("is_valid", True):
        return {}

    dev = state.get("structured_deviation") or {}
    impact = state.get("impact_assessment") or {}
    chunks = state.get("retrieved_chunks") or []
    logger.info("Node [assess_severity]: computing initial severity recommendation")

    ref_citations = [f"{c['document_name']} ({c['section']})" for c in chunks]

    user_prompt = (
        f"Deviation:\n{json.dumps(dev, indent=2)}\n\n"
        f"Quality Impact Evaluation:\n{json.dumps(impact, indent=2)}\n\n"
        f"Reference SOP Citations:\n{json.dumps(ref_citations, indent=2)}"
    )

    try:
        client, model = _get_groq_client()
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SEVERITY_ASSESSMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=2048,
        )
        sev_json = json.loads(response.choices[0].message.content or "{}")
        return {"severity_assessment": sev_json}
    except Exception as exc:
        logger.warning(
            "Node [assess_severity]: LLM severity call failed (%s). Leaving severity unassigned for human review.",
            exc,
        )
        return {
            "severity_assessment": {
                "recommended_severity": None,
                "recommended_impact": None,
                "reason": (
                    "AI initial severity recommendation unavailable due to AI service disruption. "
                    "An authorized quality reviewer must evaluate and determine severity manually."
                ),
                "evidence": ["AI service unavailable - no automated assessment performed."],
                "uncertainties": dev.get("missing_information", [])
                + ["Automated severity evaluation could not be completed."],
            }
        }


async def prepare_final_assessment_node(state: DeviationWorkflowState) -> dict[str, Any]:
    """Node 7: Assemble complete ProcessResponse."""
    settings = get_settings()

    if not state.get("is_valid", True):
        empty_dev = StructuredDeviation(
            title_short_description="Invalid input",
            detailed_description=state.get("raw_content", ""),
            missing_information=["Input failed validation"],
        )
        empty_assess = AssessmentResult(
            impact=None,
            severity=None,
            reason=state.get("validation_error") or "Input invalid",
            uncertainties=["Input too short"],
            criteria_note=CRITERIA_NOTE,
            recommended_impact=None,
            recommended_severity=None,
        )
        return {
            "final_response": {
                "deviation": empty_dev.model_dump(),
                "assessment": empty_assess.model_dump(),
                "evidence": [],
                "retrieved_sources": [],
                "rag_available": False,
                "model": settings.GROQ_MODEL or "groq",
                "provider": "groq",
                "is_stub": False,
                "error": state.get("validation_error"),
            }
        }

    dev_data = state.get("structured_deviation") or {}
    sev_data = state.get("severity_assessment") or {}
    chunks = state.get("retrieved_chunks") or []

    rec_sev_val = sev_data.get("recommended_severity")
    rec_imp_val = sev_data.get("recommended_impact")

    rec_sev: Severity | None = None
    if rec_sev_val:
        rec_sev_str = str(rec_sev_val).lower()
        if rec_sev_str in Severity._value2member_map_:
            rec_sev = Severity(rec_sev_str)

    rec_imp: Impact | None = None
    if rec_imp_val:
        rec_imp_str = str(rec_imp_val).lower()
        if rec_imp_str in Impact._value2member_map_:
            rec_imp = Impact(rec_imp_str)

    structured_dev = StructuredDeviation.model_validate(dev_data)
    evidence = sev_data.get("evidence") or structured_dev.extracted_facts

    assessment = AssessmentResult(
        impact=rec_imp,
        severity=rec_sev,
        reason=sev_data.get("reason", "Assessment based on provided deviation details."),
        evidence=evidence,
        uncertainties=sev_data.get("uncertainties") or dev_data.get("missing_information") or [],
        criteria_note=CRITERIA_NOTE,
        recommended_impact=rec_imp,
        recommended_severity=rec_sev,
    )

    retrieved_sources = [
        RetrievedSource(
            document_name=c["document_name"],
            chunk_id=c.get("chunk_id"),
            section=c.get("section"),
            page_or_chunk=c.get("page_or_chunk"),
            similarity_score=c.get("similarity_score"),
            content=c.get("content", ""),
        )
        for c in chunks
    ]

    backward_extraction = ExtractionResult(
        company=structured_dev.company,
        site_plant=structured_dev.site_plant,
        occurred_on=structured_dev.date_of_occurrence,
        date_of_occurrence=structured_dev.date_of_occurrence,
        title=structured_dev.title_short_description,
        description=structured_dev.detailed_description,
        deviation_type=structured_dev.deviation_type,
        product_name=structured_dev.related_product_material,
        batch_number=structured_dev.batch_lot_number,
        manufacturing_stage=structured_dev.manufacturing_stage,
        equipment=structured_dev.equipment,
        department=structured_dev.department,
        parameter=structured_dev.parameter,
        expected_condition=structured_dev.approved_range,
        actual_condition=structured_dev.actual_value,
        duration=structured_dev.duration,
        immediate_action=structured_dev.immediate_action,
        batch_status=BatchStatus.UNKNOWN,
    )

    final_resp = ProcessResponse(
        deviation=structured_dev,
        assessment=assessment,
        evidence=evidence,
        retrieved_sources=retrieved_sources,
        rag_available=state.get("rag_available", True),
        rag_notes=state.get("rag_notes"),
        model=settings.GROQ_MODEL,
        provider=state.get("provider", "groq"),
        is_stub=state.get("is_stub", False),
        requires_human_review=True,
        extraction=backward_extraction,
    )

    return {"final_response": final_resp.model_dump()}

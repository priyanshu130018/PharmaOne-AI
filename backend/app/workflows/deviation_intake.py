"""AI Deviation Intake Workflow using LangGraph, Groq, and Vector RAG.

Reimplements the n8n PharmaOne-AI workflow in a production-grade Python graph:
1. input validation
2. structured deviation extraction (facts vs inferences vs missing)
3. structured Pydantic output validation
4. reference retrieval via vector RAG
5. quality-risk context and impact assessment
6. initial severity recommendation (ICH Q9 decision support)
7. final structured response compilation

Architecture:
START
 ↓
validate_input
 ↓
extract_deviation
 ↓
validate_structured_output
 ↓
retrieve_reference_context
 ↓
assess_impact
 ↓
assess_severity
 ↓
prepare_final_assessment
 ↓
END
"""

from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import get_settings
from app.core.enums import (
    BatchStatus,
    DeviationSource,
    DeviationType,
    Impact,
    Severity,
)
from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.schemas.process import (
    AssessmentResult,
    ExtractionResult,
    ProcessResponse,
    RetrievedSource,
    StructuredDeviation,
)
from app.services.rag_service import RagService, RetrievedChunk

logger = get_logger("pharmaone.ai_workflow")

_CRITERIA_NOTE = (
    "Configurable/demo risk criteria — NOT a universal regulatory severity lookup. "
    "ICH Q9 is methodology guidance only. Final impact and severity must be confirmed "
    "by the reviewer against approved company procedures."
)


# ------------------------------------------------------------------------------
# State Schema
# ------------------------------------------------------------------------------


class DeviationWorkflowState(TypedDict, total=False):
    raw_content: str
    source: str
    is_valid: bool
    validation_error: str | None

    raw_extraction_output: dict[str, Any] | None
    structured_deviation: dict[str, Any] | None
    extraction_error: str | None
    repair_attempted: bool

    retrieved_chunks: list[RetrievedChunk]
    rag_available: bool
    rag_notes: str | None

    impact_assessment: dict[str, Any] | None
    severity_assessment: dict[str, Any] | None

    final_response: dict[str, Any] | None
    error: str | None
    is_stub: bool
    provider: str


# ------------------------------------------------------------------------------
# Helpers: Groq Client, Heuristic Fallbacks & Safe Invocations
# ------------------------------------------------------------------------------

_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "equipment": ("equipment", "machine", "instrument", "calibrat", "sensor", "pump", "motor", "autoclave"),
    "documentation": ("document", "record", "logbook", "sop", "batch record", "entry", "signature"),
    "material": ("material", "raw material", "excipient", "reagent", "supplier", "component"),
    "environmental": ("temperature", "humidity", "cleanroom", "environmental", "particle", "differential pressure"),
    "laboratory": ("assay", "hplc", "titration", "out of specification", "oos", "sample", "test result"),
    "personnel": ("operator", "training", "gowning", "personnel", "human error"),
    "utility": ("hvac", "water for injection", "wfi", "compressed air", "utility", "purified water"),
    "process": ("process", "mixing", "granulation", "filling", "yield", "reaction", "crystalli"),
}


def _classify_fallback_type(text: str) -> str:
    lowered = text.lower()
    best, hits = "other", 0
    for dev_type, keywords in _TYPE_KEYWORDS.items():
        n = sum(1 for kw in keywords if kw in lowered)
        if n > hits:
            best, hits = dev_type, n
    return best


def _extract_batch_regex(text: str) -> str | None:
    # 1. Explicit key-value pattern: "Batch: B-123", "Batch Number: LOT-501", "Lot: 42", "Batch - 123"
    m = re.search(
        r"\b(?:batch(?:\s*(?:number|no|#))?|lot(?:\s*(?:number|no|#))?)\s*(?:[:=]|\s+-\s+)\s*([A-Za-z0-9\-_]+)",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    # 2. Natural language pattern: "in batch B-440", "for batch LOT-501", "batch B-778"
    m = re.search(
        r"\b(?:batch|lot)\s+([A-Za-z0-9][A-Za-z0-9\-_]*)",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        return m.group(1).rstrip(".,;:").strip()
    return None


def _extract_product_regex(text: str) -> str | None:
    m = re.search(
        r"\b(?:product(?:\s*(?:name|material))?|material)\s*[:\-]\s*([^\n\r,;]+)",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()[:120] or None
    m = re.search(r"\bproduct\s+([A-Za-z0-9_\-]+)", text, flags=re.IGNORECASE)
    if m:
        return m.group(1).rstrip(".,;:").strip()
    return None


def _extract_field_regex(text: str, *labels: str) -> str | None:
    for label in labels:
        m = re.search(rf"\b{label}\b\s*[:\-]\s*(.+)", text, flags=re.IGNORECASE)
        if m:
            return m.group(1).splitlines()[0].strip()[:180] or None
    return None


def _heuristic_fallback_extraction(content: str) -> dict[str, Any]:
    dev_type = _classify_fallback_type(content)
    first_line = content.strip().splitlines()[0][:120] if content.strip() else "Deviation Event"
    product = _extract_product_regex(content)
    batch = _extract_batch_regex(content)
    equip = _extract_field_regex(content, "equipment", "instrument", "machine", "pump", "autoclave")
    dept = _extract_field_regex(content, "department", "area")
    stage = _extract_field_regex(content, "stage", "manufacturing stage", "step")
    action = _extract_field_regex(content, "immediate action", "action taken", "containment")
    param = _extract_field_regex(content, "parameter")
    exp_cond = _extract_field_regex(content, "expected", "expected condition", "limit")
    act_cond = _extract_field_regex(content, "actual", "actual condition", "observed")

    facts = [line.strip() for line in content.splitlines() if line.strip()][:5]
    missing = []
    if not batch:
        missing.append("batch_lot_number")
    if not product:
        missing.append("related_product_material")
    if not equip:
        missing.append("equipment")
    if not action:
        missing.append("immediate_action")

    return {
        "site_plant": None,
        "date_of_occurrence": None,
        "title_short_description": first_line,
        "source": "text",
        "related_product_material": product,
        "batch_lot_number": batch,
        "detailed_description": content.strip(),
        "deviation_type": dev_type,
        "manufacturing_stage": stage,
        "equipment": equip,
        "department": dept,
        "parameter": param,
        "approved_range": exp_cond,
        "actual_value": act_cond,
        "duration": None,
        "immediate_action": action,
        "qa_notified": None,
        "extracted_facts": facts,
        "inferred_information": [],
        "missing_information": missing,
    }


def _get_groq_client():
    settings = get_settings()
    if not settings.GROQ_MODEL or not settings.GROQ_MODEL.strip():
        raise ValidationError("GROQ_MODEL environment variable is required and must not be empty.")
    from groq import AsyncGroq

    return AsyncGroq(api_key=settings.GROQ_API_KEY), settings.GROQ_MODEL


# ------------------------------------------------------------------------------
# Graph Nodes
# ------------------------------------------------------------------------------


async def validate_input_node(state: DeviationWorkflowState) -> dict[str, Any]:
    """Node 1: Validate incoming deviation text length and structure."""
    content = state.get("raw_content", "")
    logger.info("Node [validate_input]: checking raw content (length=%d)", len(content))

    if not content or len(content.strip()) < 5:
        logger.warning("Node [validate_input]: content failed validation (too short)")
        return {
            "is_valid": False,
            "validation_error": "Input content is empty or shorter than 5 characters.",
            "error": "Deviation content must be at least 5 characters long.",
        }

    return {"is_valid": True, "validation_error": None}


async def extract_deviation_node(state: DeviationWorkflowState) -> dict[str, Any]:
    """Node 2: Call Groq to extract structured fields into JSON."""
    if not state.get("is_valid", True):
        return {}

    content = state["raw_content"]
    source = state.get("source", "text")
    logger.info("Node [extract_deviation]: invoking Groq LLM for extraction")

    system_prompt = (
        "You are an expert pharmaceutical Quality Assurance deviation intake specialist.\n"
        "Analyze the provided deviation text and extract structured fields adhering strictly to the AIVOA format.\n\n"
        "CRITICAL RULES:\n"
        "1. Do NOT invent, assume, or fabricate any missing values.\n"
        "2. If a field is not present in the text, you MUST return null.\n"
        "3. Explicitly distinguish:\n"
        "   - 'extracted_facts': list of facts explicitly stated in the text\n"
        "   - 'inferred_information': list of reasonable inferences with rationale\n"
        "   - 'missing_information': list of standard deviation fields that are missing\n\n"
        "Return ONLY a JSON object with this exact schema:\n"
        "{\n"
        '  "site_plant": string or null,\n'
        '  "date_of_occurrence": string or null,\n'
        '  "title_short_description": string,\n'
        '  "source": string or null,\n'
        '  "related_product_material": string or null,\n'
        '  "batch_lot_number": string or null,\n'
        '  "detailed_description": string,\n'
        '  "deviation_type": "process" | "equipment" | "documentation" | "material" | "environmental" | "personnel" | "laboratory" | "utility" | "other",\n'
        '  "manufacturing_stage": string or null,\n'
        '  "equipment": string or null,\n'
        '  "department": string or null,\n'
        '  "parameter": string or null,\n'
        '  "approved_range": string or null,\n'
        '  "actual_value": string or null,\n'
        '  "duration": string or null,\n'
        '  "immediate_action": string or null,\n'
        '  "qa_notified": boolean or null,\n'
        '  "extracted_facts": [string],\n'
        '  "inferred_information": [string],\n'
        '  "missing_information": [string]\n'
        "}"
    )

    user_prompt = f"Source Channel: {source}\n\nDeviation Content:\n{content}"

    try:
        client, model = _get_groq_client()
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        raw_text = response.choices[0].message.content or "{}"
        raw_json = json.loads(raw_text)
        logger.info("Node [extract_deviation]: LLM returned valid JSON")
        return {
            "raw_extraction_output": raw_json,
            "is_stub": False,
            "provider": "groq",
        }

    except Exception as exc:
        logger.warning("Node [extract_deviation]: Groq call failed (%s). Providing safe fallback.", exc)
        fallback_json = _heuristic_fallback_extraction(content)
        return {
            "extraction_error": f"LLM extraction error: {exc}",
            "raw_extraction_output": fallback_json,
            "is_stub": True,
            "provider": "stub",
        }


async def validate_structured_output_node(state: DeviationWorkflowState) -> dict[str, Any]:
    """Node 3: Validate LLM output against Pydantic StructuredDeviation schema."""
    if not state.get("is_valid", True):
        return {}

    raw = state.get("raw_extraction_output") or {}
    logger.info("Node [validate_structured_output]: validating schema with Pydantic")

    try:
        validated = StructuredDeviation.model_validate(raw)
        logger.info("Node [validate_structured_output]: schema validation passed")
        return {"structured_deviation": validated.model_dump()}
    except Exception as pydantic_err:
        logger.warning(
            "Node [validate_structured_output]: Pydantic validation failed: %s. Re-normalizing fields.",
            pydantic_err,
        )
        # Coerce safely into schema
        safe_dev = StructuredDeviation(
            title_short_description=str(raw.get("title_short_description") or "Deviation Event"),
            detailed_description=str(raw.get("detailed_description") or state.get("raw_content", "")),
            deviation_type=DeviationType.OTHER,
            extracted_facts=raw.get("extracted_facts") or [],
            inferred_information=raw.get("inferred_information") or [],
            missing_information=raw.get("missing_information") or ["Schema coercion applied."],
        )
        return {"structured_deviation": safe_dev.model_dump()}


async def retrieve_reference_context_node(state: DeviationWorkflowState) -> dict[str, Any]:
    """Node 4: Vector RAG retrieval of top-k reference SOPs and guidelines."""
    if not state.get("is_valid", True):
        return {}

    dev = state.get("structured_deviation") or {}
    title = dev.get("title_short_description") or ""
    param = dev.get("parameter") or ""
    equip = dev.get("equipment") or ""
    product = dev.get("related_product_material") or ""
    desc = (dev.get("detailed_description") or "")[:150]

    query = f"{title} {param} {equip} {product} {desc}".strip()
    logger.info("Node [retrieve_reference_context]: querying vector RAG with '%s'", query[:80])

    try:
        rag_service = RagService.get_instance()
        chunks, success, message = rag_service.retrieve(query, top_k=3)
        return {
            "retrieved_chunks": chunks,
            "rag_available": success,
            "rag_notes": message,
        }
    except Exception as rag_err:
        logger.warning("Node [retrieve_reference_context]: RAG retrieval failed safely: %s", rag_err)
        return {
            "retrieved_chunks": [],
            "rag_available": False,
            "rag_notes": f"RAG retrieval unavailable ({rag_err.__class__.__name__}).",
        }


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

    system_prompt = (
        "You are an expert pharmaceutical Quality Risk Management specialist.\n"
        "Evaluate the quality, product, and process impact of the deviation using the retrieved SOP context.\n"
        "DO NOT assign a final regulatory severity in this step.\n"
        "Focus on: critical quality attributes (CQAs), hazard identification, contamination risk, "
        "and uncertainties.\n\n"
        "Return ONLY a JSON object with this schema:\n"
        "{\n"
        '  "risk_factors": [string],\n'
        '  "potential_product_impact": string,\n'
        '  "quality_risk_considerations": [string],\n'
        '  "uncertainties": [string]\n'
        "}"
    )

    user_prompt = (
        f"Deviation Details:\n{json.dumps(dev, indent=2)}\n\n"
        f"Retrieved Reference Context:\n{ref_text}"
    )

    try:
        client, model = _get_groq_client()
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        impact_json = json.loads(response.choices[0].message.content or "{}")
        return {"impact_assessment": impact_json}
    except Exception as exc:
        logger.warning("Node [assess_impact]: LLM impact assessment call failed (%s). Using fallback.", exc)
        return {
            "impact_assessment": {
                "risk_factors": ["Potential process variation"],
                "potential_product_impact": "Requires quality investigation against batch release criteria.",
                "quality_risk_considerations": ["Verify product critical quality attributes"],
                "uncertainties": dev.get("missing_information", []),
            }
        }


async def assess_severity_node(state: DeviationWorkflowState) -> dict[str, Any]:
    """Node 6: Initial AI severity recommendation (ICH Q9 decision support)."""
    if not state.get("is_valid", True):
        return {}

    dev = state.get("structured_deviation") or {}
    impact = state.get("impact_assessment") or {}
    chunks = state.get("retrieved_chunks") or []
    logger.info("Node [assess_severity]: computing initial severity recommendation")

    ref_citations = [f"{c['document_name']} ({c['section']})" for c in chunks]

    system_prompt = (
        "You are an expert pharmaceutical Quality Assurance director.\n"
        "Recommend an initial deviation severity (minor, major, critical) and impact area.\n"
        "Criteria:\n"
        "- critical: direct risk to patient safety, sterility failure, endotoxin contamination, or product recall\n"
        "- major: out of specification (OOS), stability failure, critical parameter breach affecting product quality\n"
        "- minor: isolated documentation error or non-critical process variation without product quality impact\n\n"
        "Return ONLY a JSON object with this schema:\n"
        "{\n"
        '  "recommended_severity": "minor" | "major" | "critical",\n'
        '  "recommended_impact": "patient_safety" | "product_quality" | "data_integrity" | "compliance" | "supply" | "none",\n'
        '  "reason": string,\n'
        '  "evidence": [string],\n'
        '  "uncertainties": [string]\n'
        "}"
    )

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
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        sev_json = json.loads(response.choices[0].message.content or "{}")
        return {"severity_assessment": sev_json}
    except Exception as exc:
        logger.warning("Node [assess_severity]: LLM severity call failed (%s). Using rule-based fallback.", exc)
        desc_lower = str(dev.get("detailed_description", "")).lower()
        if any(w in desc_lower for w in ("sterility", "contaminat", "patient", "endotoxin", "recall")):
            rec_sev, rec_imp = Severity.CRITICAL, Impact.PATIENT_SAFETY
            reason = "Content mentions sterility, contamination, or patient safety risk factors."
        elif any(w in desc_lower for w in ("out of specification", "oos", "excursion", "failure", "abort")):
            rec_sev, rec_imp = Severity.MAJOR, Impact.PRODUCT_QUALITY
            reason = "Content mentions specification failure or process excursion."
        else:
            rec_sev, rec_imp = Severity.MINOR, Impact.PRODUCT_QUALITY
            reason = "No high-risk terminology detected; provisional minor classification."

        return {
            "severity_assessment": {
                "recommended_severity": rec_sev.value,
                "recommended_impact": rec_imp.value,
                "reason": reason,
                "evidence": [f"Evaluated from text: {dev.get('title_short_description')}"],
                "uncertainties": dev.get("missing_information", []),
            }
        }


async def prepare_final_assessment_node(state: DeviationWorkflowState) -> dict[str, Any]:
    """Node 7: Assemble complete ProcessResponse."""
    settings = get_settings()

    if not state.get("is_valid", True):
        # Return structured error representation
        empty_dev = StructuredDeviation(
            title_short_description="Invalid input",
            detailed_description=state.get("raw_content", ""),
            missing_information=["Input failed validation"],
        )
        empty_assess = AssessmentResult(
            impact=Impact.NONE,
            severity=Severity.MINOR,
            reason=state.get("validation_error") or "Input invalid",
            uncertainties=["Input too short"],
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

    # Map recommended severity & impact enums
    rec_sev_str = str(sev_data.get("recommended_severity", "minor")).lower()
    rec_imp_str = str(sev_data.get("recommended_impact", "product_quality")).lower()

    rec_sev = (
        Severity(rec_sev_str)
        if rec_sev_str in Severity._value2member_map_
        else Severity.MINOR
    )
    rec_imp = (
        Impact(rec_imp_str)
        if rec_imp_str in Impact._value2member_map_
        else Impact.PRODUCT_QUALITY
    )

    structured_dev = StructuredDeviation.model_validate(dev_data)
    evidence = sev_data.get("evidence") or structured_dev.extracted_facts

    assessment = AssessmentResult(
        impact=rec_imp,
        severity=rec_sev,
        reason=sev_data.get("reason", "Assessment based on provided deviation details."),
        evidence=evidence,
        uncertainties=sev_data.get("uncertainties") or dev_data.get("missing_information") or [],
        criteria_note=_CRITERIA_NOTE,
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

    # Build backward-compatible extraction mapping for editable form UI
    backward_extraction = ExtractionResult(
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


# ------------------------------------------------------------------------------
# Build and Compile LangGraph Workflow
# ------------------------------------------------------------------------------


def create_deviation_intake_graph() -> Any:
    """Build the LangGraph workflow for AI deviation intake."""
    workflow = StateGraph(DeviationWorkflowState)

    workflow.add_node("validate_input", validate_input_node)
    workflow.add_node("extract_deviation", extract_deviation_node)
    workflow.add_node("validate_structured_output", validate_structured_output_node)
    workflow.add_node("retrieve_reference_context", retrieve_reference_context_node)
    workflow.add_node("assess_impact", assess_impact_node)
    workflow.add_node("assess_severity", assess_severity_node)
    workflow.add_node("prepare_final_assessment", prepare_final_assessment_node)

    # Graph Edges
    workflow.add_edge(START, "validate_input")

    # Conditional edge: if invalid, jump straight to response preparation
    workflow.add_conditional_edges(
        "validate_input",
        lambda state: "extract_deviation" if state.get("is_valid", True) else "prepare_final_assessment",
    )

    workflow.add_edge("extract_deviation", "validate_structured_output")
    workflow.add_edge("validate_structured_output", "retrieve_reference_context")
    workflow.add_edge("retrieve_reference_context", "assess_impact")
    workflow.add_edge("assess_impact", "assess_severity")
    workflow.add_edge("assess_severity", "prepare_final_assessment")
    workflow.add_edge("prepare_final_assessment", END)

    return workflow.compile()


# Single compiled graph instance
deviation_graph = create_deviation_intake_graph()


# ------------------------------------------------------------------------------
# Public Interface
# ------------------------------------------------------------------------------


async def process_deviation(
    *,
    content: str,
    source: DeviationSource = DeviationSource.TEXT,
) -> ProcessResponse:
    """Execute the complete LangGraph AI Deviation Intake workflow.

    Coordinates:
    Input validation -> Groq extraction -> Pydantic validation -> Vector RAG ->
    Quality impact analysis -> Severity recommendation -> ProcessResponse
    """
    initial_state: DeviationWorkflowState = {
        "raw_content": content,
        "source": source.value if hasattr(source, "value") else str(source),
        "is_valid": True,
        "retrieved_chunks": [],
        "rag_available": True,
    }

    final_state = await deviation_graph.ainvoke(initial_state)

    resp_data = final_state.get("final_response")
    if not resp_data:
        raise ValidationError("AI deviation processing did not generate a valid response.")

    return ProcessResponse.model_validate(resp_data)

"""LangGraph workflow definition for AI Deviation Intake."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.ai.extraction import (
    extract_deviation_node,
    validate_input_node,
    validate_structured_output_node,
)
from app.ai.models import DeviationWorkflowState
from app.ai.risk_assessment import (
    assess_impact_node,
    assess_severity_node,
    prepare_final_assessment_node,
)
from app.core.enums import DeviationSource
from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.schemas.process import ProcessResponse
from app.rag.service import RagService

logger = get_logger("pharmaone.ai_graph")


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
        chunks, success, message = await rag_service.asearch(query, top_k=3)
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


def create_deviation_intake_graph() -> Any:
    """Build and compile the LangGraph workflow for AI deviation intake."""
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


deviation_graph = create_deviation_intake_graph()


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

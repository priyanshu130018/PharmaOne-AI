"""AI module for PharmaOne-AI deviation processing."""

from app.ai.extraction import (
    _get_groq_client,
    _heuristic_fallback_extraction,
    extract_deviation_node,
    validate_input_node,
    validate_structured_output_node,
)
from app.ai.graph import (
    create_deviation_intake_graph,
    deviation_graph,
    process_deviation,
    retrieve_reference_context_node,
)
from app.ai.models import DeviationWorkflowState
from app.ai.prompts import (
    CRITERIA_NOTE,
    DEVIATION_EXTRACTION_SYSTEM_PROMPT,
    IMPACT_ASSESSMENT_SYSTEM_PROMPT,
    SEVERITY_ASSESSMENT_SYSTEM_PROMPT,
)
from app.ai.risk_assessment import (
    assess_impact_node,
    assess_severity_node,
    prepare_final_assessment_node,
)

__all__ = [
    "create_deviation_intake_graph",
    "deviation_graph",
    "process_deviation",
    "DeviationWorkflowState",
    "validate_input_node",
    "extract_deviation_node",
    "validate_structured_output_node",
    "retrieve_reference_context_node",
    "assess_impact_node",
    "assess_severity_node",
    "prepare_final_assessment_node",
    "DEVIATION_EXTRACTION_SYSTEM_PROMPT",
    "IMPACT_ASSESSMENT_SYSTEM_PROMPT",
    "SEVERITY_ASSESSMENT_SYSTEM_PROMPT",
    "CRITERIA_NOTE",
    "_get_groq_client",
    "_heuristic_fallback_extraction",
]

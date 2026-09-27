"""State definitions and models for the AI Deviation Intake workflow."""

from __future__ import annotations

from typing import Any, TypedDict

from app.schemas.process import (
    AssessmentResult,
    ExtractionResult,
    ProcessRequest,
    ProcessResponse,
    RetrievedSource,
    StructuredDeviation,
)
from app.rag.retrieval import RetrievedChunk


class DeviationWorkflowState(TypedDict, total=False):
    """LangGraph state schema for deviation intake execution."""

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


__all__ = [
    "DeviationWorkflowState",
    "ProcessRequest",
    "ProcessResponse",
    "StructuredDeviation",
    "AssessmentResult",
    "RetrievedSource",
    "ExtractionResult",
]

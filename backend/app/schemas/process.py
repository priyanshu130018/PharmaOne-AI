"""Pydantic schemas for the AI Deviation Intake workflow.

Defines the structured deviation schema, RAG retrieved source schema,
and risk assessment responses. Strictly distinguishes extracted facts,
inferences, and missing information.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.enums import (
    BatchStatus,
    DeviationSource,
    DeviationType,
    Impact,
    Severity,
)


class ProcessRequest(BaseModel):
    """Raw deviation content the user pastes/uploads for AI processing."""

    content: str = Field(..., min_length=5, description="Deviation text / email content")
    source: DeviationSource = DeviationSource.TEXT


class StructuredDeviation(BaseModel):
    """Structured deviation fields extracted by the AI from normalized content.

    Distinguishes facts directly stated in the source from inferred information
    and explicitly identified missing data. Does not invent or fabricate values.
    """

    site_plant: str | None = Field(
        default=None,
        description="Manufacturing site or facility name",
    )
    date_of_occurrence: str | None = Field(
        default=None,
        description="Date or timestamp of deviation occurrence",
    )
    title_short_description: str | None = Field(
        default=None,
        description="Short summary title of the deviation",
    )
    source: str | None = Field(
        default=None,
        description="Source classification or document reference",
    )
    related_product_material: str | None = Field(
        default=None,
        description="Product name or material identifier",
    )
    batch_lot_number: str | None = Field(
        default=None,
        description="Batch number or lot identifier",
    )
    detailed_description: str | None = Field(
        default=None,
        description="Detailed description of what occurred",
    )
    deviation_type: DeviationType | None = Field(
        default=None,
        description="Classified deviation type",
    )
    manufacturing_stage: str | None = Field(
        default=None,
        description="Process step or manufacturing stage",
    )
    equipment: str | None = Field(
        default=None,
        description="Equipment, machine, or instrument involved",
    )
    department: str | None = Field(
        default=None,
        description="Department or functional area",
    )
    parameter: str | None = Field(
        default=None,
        description="Physical/chemical/biological parameter monitored",
    )
    approved_range: str | None = Field(
        default=None,
        description="Validated limit or approved range",
    )
    actual_value: str | None = Field(
        default=None,
        description="Observed or measured excursion value",
    )
    duration: str | None = Field(
        default=None,
        description="Duration of excursion or event",
    )
    immediate_action: str | None = Field(
        default=None,
        description="Containment or immediate action taken",
    )
    qa_notified: bool | None = Field(
        default=None,
        description="Whether QA was notified",
    )

    # Distinct categorization of information types
    extracted_facts: list[str] = Field(
        default_factory=list,
        description="Factual assertions directly extracted from the input text.",
    )
    inferred_information: list[str] = Field(
        default_factory=list,
        description="Plausible inferences derived from context with AI reasoning.",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description="Explicitly identified fields not present in the input text.",
    )


class AssessmentResult(BaseModel):
    """Initial quality-risk assessment recommendation for human review."""

    impact: Impact | None = Field(default=None, description="Recommended quality impact area (None if unavailable)")
    severity: Severity | None = Field(default=None, description="Recommended initial severity level (None if unavailable)")
    reason: str = Field(..., description="Justification grounded in GMP and reference context")
    evidence: list[str] = Field(
        default_factory=list,
        description="Factual observations and reference citations supporting the recommendation",
    )
    uncertainties: list[str] = Field(
        default_factory=list,
        description="Unverified assumptions or missing data affecting the assessment",
    )
    criteria_note: str = Field(
        default=(
            "AI initial severity recommendation based on the deviation information and retrieved quality-risk context. "
            "Advisory only — final impact and severity must be confirmed and approved by authorized quality personnel."
        ),
        description="Governance notice clarifying that AI output is decision support.",
    )
    recommended_impact: Impact | None = None
    recommended_severity: Severity | None = None


class RetrievedSource(BaseModel):
    """Source reference retrieved from the pharmaceutical knowledge base."""

    document_name: str
    chunk_id: str | None = None
    section: str | None = None
    page_or_chunk: str | None = None
    similarity_score: float | None = None
    content: str


class ExtractionResult(BaseModel):
    """Backward-compatible mapping of structured fields for the editable form."""

    title: str | None = None
    description: str | None = None
    deviation_type: DeviationType | None = None
    product_name: str | None = None
    product_code: str | None = None
    batch_number: str | None = None
    manufacturing_stage: str | None = None
    equipment: str | None = None
    department: str | None = None
    responsible_team: str | None = None
    expected_condition: str | None = None
    actual_condition: str | None = None
    duration: str | None = None
    parameter: str | None = None
    immediate_action: str | None = None
    batch_status: BatchStatus | None = None


class RiskAssessment(BaseModel):
    """Backward-compatible risk assessment model."""

    recommended_impact: Impact
    recommended_severity: Severity
    reason: str
    evidence: list[str] = Field(default_factory=list)
    retrieved_sources: list[str] = Field(default_factory=list)
    deterministic_checks: list[str] = Field(default_factory=list)
    criteria_note: str


class ProcessResponse(BaseModel):
    """Complete response returned by the AI Deviation Intake workflow."""

    deviation: StructuredDeviation
    assessment: AssessmentResult
    evidence: list[str] = Field(default_factory=list)
    retrieved_sources: list[RetrievedSource] = Field(default_factory=list)
    rag_available: bool = True
    rag_notes: str | None = None
    model: str = Field(..., description="Groq model identifier used for extraction and assessment")
    provider: str = Field(default="groq", description="AI provider")
    is_stub: bool = False
    requires_human_review: bool = True

    # Backward-compatible fields for UI
    extraction: ExtractionResult | None = None

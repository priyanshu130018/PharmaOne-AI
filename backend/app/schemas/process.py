from pydantic import BaseModel, Field

from app.core.enums import (
    BatchStatus,
    DeviationSource,
    DeviationType,
    Impact,
    Severity,
)


class ProcessRequest(BaseModel):
    """Raw deviation content the user pastes/uploads for AI processing.

    For this foundation only `content` (text/email body) is accepted. PDF
    upload + OCR is a documented next step; the contract will not change.
    """

    content: str = Field(..., min_length=5, description="Deviation text / email content")
    source: DeviationSource = DeviationSource.TEXT


class ExtractionResult(BaseModel):
    """Structured deviation fields extracted by the AI from raw content.

    Mirrors the editable Log Deviation form fields. Everything is optional
    because extraction is best-effort and the user reviews/edits before save.
    """

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
    """AI-assisted risk output. Decision support only — human review required.

    `criteria_note` labels the basis as configurable/demo criteria, per the
    AIVOA governance requirement (not a universal regulatory severity lookup).
    """

    recommended_impact: Impact
    recommended_severity: Severity
    reason: str
    evidence: list[str] = Field(default_factory=list)
    retrieved_sources: list[str] = Field(default_factory=list)
    deterministic_checks: list[str] = Field(default_factory=list)
    criteria_note: str


class ProcessResponse(BaseModel):
    extraction: ExtractionResult
    assessment: RiskAssessment
    model: str = Field(..., description="Model identifier configured for the workflow")
    provider: str = Field(..., examples=["groq", "stub"])
    is_stub: bool = Field(
        ...,
        description="True when produced by the offline heuristic stub rather than a live LLM/RAG pipeline.",
    )
    requires_human_review: bool = True

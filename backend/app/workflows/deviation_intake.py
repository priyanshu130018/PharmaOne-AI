"""AI Deviation Intake workflow.

Single home for AI orchestration. This foundation ships an *offline heuristic
stub* so the whole flow runs with no network/LLM dependency. The public
surface (`process_deviation`) is exactly what the future LangGraph + Groq + RAG
pipeline will implement, so the service and API layers won't change when the
real implementation is dropped in.

Pipeline the real version will follow (see AIVOA Workflow spec):
    text/PDF -> (OCR if needed) -> structured extraction -> Pydantic validation
    -> query embedding -> vector retrieval -> deterministic checks
    -> risk assessment/explanation -> human review -> save

No provider URLs/keys/model names are hardcoded here; the configured model
name is read from settings and echoed back for traceability.
"""

from __future__ import annotations

import re

from app.core.config import get_settings
from app.core.enums import (
    BatchStatus,
    DeviationSource,
    DeviationType,
    Impact,
    Severity,
)
from app.schemas.process import (
    ExtractionResult,
    ProcessResponse,
    RiskAssessment,
)

_TYPE_KEYWORDS: dict[DeviationType, tuple[str, ...]] = {
    DeviationType.EQUIPMENT: ("equipment", "machine", "instrument", "calibrat", "sensor", "pump", "motor"),
    DeviationType.DOCUMENTATION: ("document", "record", "logbook", "sop", "batch record", "entry", "signature"),
    DeviationType.MATERIAL: ("material", "raw material", "excipient", "reagent", "supplier", "component"),
    DeviationType.ENVIRONMENTAL: ("temperature", "humidity", "cleanroom", "environmental", "particle", "differential pressure"),
    DeviationType.LABORATORY: ("assay", "hplc", "titration", "out of specification", "oos", "sample", "test result"),
    DeviationType.PERSONNEL: ("operator", "training", "gowning", "personnel", "human error"),
    DeviationType.UTILITY: ("hvac", "water for injection", "wfi", "compressed air", "utility", "purified water"),
    DeviationType.PROCESS: ("process", "mixing", "granulation", "filling", "yield", "reaction", "crystalli"),
}

_CRITICAL_KEYWORDS = ("contaminat", "sterility", "patient", "recall", "cross-contamin", "endotoxin", "adverse event")
_MAJOR_KEYWORDS = ("out of specification", "oos", "stability", "impurity", "batch reject", "excursion", "failure")

_IMPACT_KEYWORDS: dict[Impact, tuple[str, ...]] = {
    Impact.PATIENT_SAFETY: ("patient", "sterility", "contaminat", "endotoxin", "adverse"),
    Impact.DATA_INTEGRITY: ("data", "record", "logbook", "signature", "audit trail"),
    Impact.COMPLIANCE: ("sop", "procedure", "gmp", "regulat"),
    Impact.SUPPLY: ("supplier", "material", "shortage", "delay"),
    Impact.PRODUCT_QUALITY: ("impurity", "assay", "specification", "yield", "quality"),
}

_CRITERIA_NOTE = (
    "Configurable/demo risk criteria — NOT a universal regulatory severity "
    "lookup. ICH Q9 is methodology guidance only. Final impact/severity must "
    "be confirmed by the reviewer against approved company procedures."
)


def _first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip(" \t-•*#").strip()
        if cleaned:
            return cleaned
    return text.strip()


def _classify_type(text: str) -> DeviationType:
    lowered = text.lower()
    best, hits = DeviationType.OTHER, 0
    for dev_type, keywords in _TYPE_KEYWORDS.items():
        n = sum(1 for kw in keywords if kw in lowered)
        if n > hits:
            best, hits = dev_type, n
    return best


def _classify_severity(text: str) -> tuple[Severity, str]:
    lowered = text.lower()
    if any(kw in lowered for kw in _CRITICAL_KEYWORDS):
        return Severity.CRITICAL, "Language indicates potential product-safety or patient impact."
    if any(kw in lowered for kw in _MAJOR_KEYWORDS):
        return Severity.MAJOR, "Language indicates a specification/quality-attribute impact."
    return Severity.MINOR, "No safety- or specification-impacting signals detected in the text."


def _classify_impact(text: str) -> Impact:
    lowered = text.lower()
    for impact, keywords in _IMPACT_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return impact
    return Impact.PRODUCT_QUALITY


def _extract_field(text: str, *labels: str) -> str | None:
    """Very small label-based extractor, e.g. 'Batch: 1234'."""
    for label in labels:
        m = re.search(rf"{label}\s*[:\-]\s*(.+)", text, flags=re.IGNORECASE)
        if m:
            return m.group(1).splitlines()[0].strip()[:180] or None
    return None


def _build_extraction(text: str) -> ExtractionResult:
    dev_type = _classify_type(text)
    title = _first_nonempty_line(text)[:120]
    return ExtractionResult(
        title=title or None,
        description=text.strip(),
        deviation_type=dev_type,
        product_name=_extract_field(text, "product", "product name"),
        product_code=_extract_field(text, "product code", "material code"),
        batch_number=_extract_field(text, "batch", "batch no", "lot"),
        manufacturing_stage=_extract_field(text, "stage", "manufacturing stage", "step"),
        equipment=_extract_field(text, "equipment", "instrument", "machine"),
        department=_extract_field(text, "department", "area"),
        responsible_team=_extract_field(text, "team", "responsible team"),
        expected_condition=_extract_field(text, "expected", "expected condition", "limit"),
        actual_condition=_extract_field(text, "actual", "actual condition", "observed"),
        duration=_extract_field(text, "duration", "for"),
        parameter=_extract_field(text, "parameter"),
        immediate_action=_extract_field(text, "immediate action", "action taken", "containment"),
        batch_status=BatchStatus.UNKNOWN,
    )


def _build_assessment(text: str) -> RiskAssessment:
    severity, reason = _classify_severity(text)
    impact = _classify_impact(text)
    lowered = text.lower()

    evidence: list[str] = []
    for kw in (*_CRITICAL_KEYWORDS, *_MAJOR_KEYWORDS):
        if kw in lowered:
            evidence.append(f"Detected term related to '{kw}' in the description.")
    if not evidence:
        evidence.append("No high-risk terms detected; provisional low-severity classification.")

    return RiskAssessment(
        recommended_impact=impact,
        recommended_severity=severity,
        reason=reason,
        evidence=evidence[:5],
        retrieved_sources=[],  # RAG retrieval not wired in this foundation.
        deterministic_checks=[
            "No approved numeric limits configured in this demo; deterministic "
            "comparison skipped. When limits exist they run before the LLM step.",
        ],
        criteria_note=_CRITERIA_NOTE,
    )


async def process_deviation(*, content: str, source: DeviationSource) -> ProcessResponse:
    """Extract structured fields and produce a risk assessment for review.

    Current implementation: deterministic offline heuristic (no network call).
    """
    settings = get_settings()
    extraction = _build_extraction(content)
    assessment = _build_assessment(content)

    return ProcessResponse(
        extraction=extraction,
        assessment=assessment,
        model=settings.GROQ_MODEL,
        provider="stub",
        is_stub=True,
        requires_human_review=True,
    )

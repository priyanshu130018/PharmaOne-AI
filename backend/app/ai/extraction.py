"""Extraction nodes and heuristic fallback logic for AI Deviation Intake."""

from __future__ import annotations

import json
import re
from typing import Any

from app.ai.models import DeviationWorkflowState
from app.ai.prompts import DEVIATION_EXTRACTION_SYSTEM_PROMPT
from app.core.config import get_settings
from app.core.enums import DeviationType
from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.schemas.process import StructuredDeviation

logger = get_logger("pharmaone.ai_extraction")

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
    # 1. Explicit key-value pattern: "Batch: LOT-2026-042", "Batch Number: LOT-501", "Lot # 42", "Batch - 123"
    m = re.search(
        r"\b(?:batch(?:\s*(?:number|no|#|id))?|lot(?:\s*(?:number|no|#|id))?)\s*[:=\-#\s]\s*([A-Za-z0-9\-_]+)",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        val = m.group(1).strip()
        if len(val) >= 2 and val.lower() not in ("of", "for", "the", "in", "and", "is", "was"):
            return val
    # 2. Explicit LOT/BATCH prefix pattern: e.g. LOT-2026-042, BATCH-1049, BN-992
    m = re.search(
        r"\b((?:LOT|BATCH|BN)[\-_][A-Za-z0-9\-_]+)\b",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    # 3. Natural language pattern: "in batch B-440", "for batch LOT-501", "batch B-778"
    m = re.search(
        r"\b(?:batch|lot)\s+([A-Za-z0-9][A-Za-z0-9\-_]*)",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        val = m.group(1).rstrip(".,;:").strip()
        if len(val) >= 2 and val.lower() not in ("of", "for", "the", "in", "and", "is", "was"):
            return val
    return None


_MONTHS: dict[str, str] = {
    "january": "01", "jan": "01", "february": "02", "feb": "02", "march": "03", "mar": "03",
    "april": "04", "apr": "04", "may": "05", "june": "06", "jun": "06",
    "july": "07", "jul": "07", "august": "08", "aug": "08", "september": "09", "sep": "09", "sept": "09",
    "october": "10", "oct": "10", "november": "11", "nov": "11", "december": "12", "dec": "12",
}


def _extract_date_regex(text: str) -> str | None:
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b", text)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    m = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b", text)
    if m and m.group(2).lower() in _MONTHS:
        return f"{m.group(3)}-{_MONTHS[m.group(2).lower()]}-{m.group(1).zfill(2)}"
    m = re.search(r"\b([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})\b", text)
    if m and m.group(1).lower() in _MONTHS:
        return f"{m.group(3)}-{_MONTHS[m.group(1).lower()]}-{m.group(2).zfill(2)}"
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

    qa_notified = None
    if re.search(
        r"\b(?:qa|quality assurance)\s+(?:was\s+)?not\s+(?:notified|informed)\b",
        content,
        re.IGNORECASE,
    ):
        qa_notified = False
    elif re.search(
        r"(?:\b(?:qa|quality assurance)\s+(?:(?:was|were)\s+)?(?:notified|informed)\b|"
        r"\b(?:notified|informed)\b[^.\n]{0,100}\b(?:qa|quality assurance)\b)",
        content,
        re.IGNORECASE,
    ):
        qa_notified = True

    duration = None
    m_dur = re.search(
        r"\b(?:for|duration(?:\s*of)?)\s+(?:approximately\s+|approx\.?\s+)?([0-9]+(?:\.[0-9]+)?\s*(?:minutes?|hours?|mins?|hrs?|seconds?|secs?|days?))\b",
        content,
        re.IGNORECASE,
    )
    if m_dur:
        duration = m_dur.group(1).strip()
    else:
        m_dur2 = re.search(
            r"\b([0-9]+(?:\.[0-9]+)?\s*-\s*minutes?|[0-9]+(?:\.[0-9]+)?\s*-\s*hours?)\b",
            content,
            re.IGNORECASE,
        )
        if m_dur2:
            duration = m_dur2.group(1).strip()

    if not exp_cond:
        m_range = re.search(
            r"\bapproved\s*(?:temperature|pressure|speed|pH)?\s*(?:range|limit|spec(?:ification)?)\s*(?:was|is)?\s*[:\-]?\s*([0-9\.\–\-\s°CcFf]+)",
            content,
            re.IGNORECASE,
        )
        if m_range:
            exp_cond = m_range.group(1).rstrip(".,;:").strip()

    if not act_cond:
        m_act = re.search(
            r"\b(?:actual\s*(?:temperature|pressure|speed|pH)?\s*(?:reached|was|is)?\s*[:\-]?|(?:dropped to|rose to|reached|measured at|recorded at)\s*)([0-9]+(?:\.[0-9]+)?\s*°?[CcFf]?)",
            content,
            re.IGNORECASE,
        )
        if m_act:
            act_cond = m_act.group(1).rstrip(".,;:").strip()

    if not param:
        if re.search(r"\btemperature\b", content, re.IGNORECASE):
            param = "Temperature"
        elif re.search(r"\bpressure\b", content, re.IGNORECASE):
            param = "Pressure"
        elif re.search(r"\bph\b", content, re.IGNORECASE):
            param = "pH"

    if not action:
        m_act_sent = re.search(
            r"\b(?:production|line|process|operation)\s+was\s+stopped[^.\n]*",
            content,
            re.IGNORECASE,
        )
        if m_act_sent:
            action = m_act_sent.group(0).strip()

    missing = []
    if not batch:
        missing.append("batch_lot_number")
    if not product:
        missing.append("related_product_material")
    if not equip:
        missing.append("equipment")
    if not action:
        missing.append("immediate_action")

    date_val = _extract_date_regex(content)
    company_val = _extract_field_regex(content, "company", "organization", "corp")
    site_val = _extract_field_regex(content, "site", "plant", "site / plant", "site/plant", "facility", "manufacturing site")
    if site_val and company_val and site_val.lower() == company_val.lower():
        site_val = None

    return {
        "company": company_val,
        "site_plant": site_val,
        "date_of_occurrence": date_val,
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
        "duration": duration,
        "immediate_action": action,
        "qa_notified": qa_notified,
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

    user_prompt = f"Source Channel: {source}\n\nDeviation Content:\n{content}"

    try:
        client, model = _get_groq_client()
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": DEVIATION_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=4096,
        )
        raw_text = response.choices[0].message.content or "{}"
        raw_json = json.loads(raw_text)
        logger.info("Node [extract_deviation]: LLM returned valid JSON")

        # Fallback enrichment: Ensure site_plant, company, date_of_occurrence are populated if explicitly in content
        if not raw_json.get("site_plant"):
            site_val = _extract_field_regex(content, "site", "plant", "site / plant", "site/plant", "facility", "manufacturing site")
            comp_val = raw_json.get("company") or _extract_field_regex(content, "company", "organization", "corp")
            if site_val and (not comp_val or site_val.lower() != comp_val.lower()):
                raw_json["site_plant"] = site_val
                if "site_plant" in raw_json.get("missing_information", []):
                    raw_json["missing_information"].remove("site_plant")
        if not raw_json.get("company"):
            comp_val = _extract_field_regex(content, "company", "organization", "corp")
            if comp_val:
                raw_json["company"] = comp_val
        if not raw_json.get("date_of_occurrence"):
            date_val = _extract_date_regex(content)
            if date_val:
                raw_json["date_of_occurrence"] = date_val
                if "date_of_occurrence" in raw_json.get("missing_information", []):
                    raw_json["missing_information"].remove("date_of_occurrence")

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
        # Coerce safely into schema while preserving all extracted fields
        safe_dev = StructuredDeviation(
            company=raw.get("company"),
            site_plant=raw.get("site_plant"),
            date_of_occurrence=raw.get("date_of_occurrence"),
            title_short_description=str(raw.get("title_short_description") or "Deviation Event"),
            detailed_description=str(raw.get("detailed_description") or state.get("raw_content", "")),
            deviation_type=DeviationType.OTHER,
            source=raw.get("source"),
            related_product_material=raw.get("related_product_material"),
            batch_lot_number=raw.get("batch_lot_number"),
            manufacturing_stage=raw.get("manufacturing_stage"),
            equipment=raw.get("equipment"),
            department=raw.get("department"),
            parameter=raw.get("parameter"),
            approved_range=raw.get("approved_range"),
            actual_value=raw.get("actual_value"),
            duration=raw.get("duration"),
            immediate_action=raw.get("immediate_action"),
            qa_notified=raw.get("qa_notified") if isinstance(raw.get("qa_notified"), bool) else None,
            extracted_facts=raw.get("extracted_facts") or [],
            inferred_information=raw.get("inferred_information") or [],
            missing_information=raw.get("missing_information") or ["Schema coercion applied."],
        )
        return {"structured_deviation": safe_dev.model_dump()}

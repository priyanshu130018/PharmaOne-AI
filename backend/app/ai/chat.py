"""Context-aware AI Deviation Intake Chat service."""

from __future__ import annotations

import json
import re
from typing import Any

from app.ai.extraction import _get_groq_client
from app.ai.prompts import DEVIATION_CHAT_SYSTEM_PROMPT
from app.core.logging import get_logger
from app.schemas.chat import DeviationChatRequest, DeviationChatResponse, FormFieldChange

logger = get_logger("pharmaone.ai_chat")

ALLOWED_FORM_FIELDS: set[str] = {
    "site_plant",
    "occurred_on",
    "detected_on",
    "title",
    "source",
    "product_name",
    "product_code",
    "batch_number",
    "description",
    "deviation_type",
    "impact",
    "severity",
    "parameter",
    "expected_condition",
    "actual_condition",
    "duration",
    "manufacturing_stage",
    "equipment",
    "department",
    "responsible_team",
    "immediate_action",
    "qa_notified",
    "batch_status",
    "company",
    "reported_by",
    "assessment_reason",
}

FIELD_ALIAS_MAP: dict[str, str] = {
    "site": "site_plant",
    "plant": "site_plant",
    "site_plant": "site_plant",
    "facility": "site_plant",
    "date": "occurred_on",
    "date_of_occurrence": "occurred_on",
    "occurred_on": "occurred_on",
    "occurrence_date": "occurred_on",
    "incident_date": "occurred_on",
    "detected_on": "detected_on",
    "date_detected": "detected_on",
    "title": "title",
    "title_short_description": "title",
    "short_description": "title",
    "source": "source",
    "source_channel": "source",
    "product": "product_name",
    "product_name": "product_name",
    "related_product": "product_name",
    "related_product_material": "product_name",
    "material": "product_name",
    "product_code": "product_code",
    "batch": "batch_number",
    "batch_number": "batch_number",
    "batch_lot_number": "batch_number",
    "batch_lot": "batch_number",
    "lot": "batch_number",
    "lot_number": "batch_number",
    "description": "description",
    "detailed_description": "description",
    "deviation_type": "deviation_type",
    "type": "deviation_type",
    "impact": "impact",
    "initial_impact": "impact",
    "severity": "severity",
    "initial_severity": "severity",
    "parameter": "parameter",
    "expected_condition": "expected_condition",
    "approved_range": "expected_condition",
    "expected_value": "expected_condition",
    "expected": "expected_condition",
    "actual_condition": "actual_condition",
    "actual_value": "actual_condition",
    "actual": "actual_condition",
    "duration": "duration",
    "manufacturing_stage": "manufacturing_stage",
    "stage": "manufacturing_stage",
    "equipment": "equipment",
    "asset": "equipment",
    "machine": "equipment",
    "department": "department",
    "responsible_team": "responsible_team",
    "immediate_action": "immediate_action",
    "action": "immediate_action",
    "containment_action": "immediate_action",
    "qa_notified": "qa_notified",
    "batch_status": "batch_status",
    "company": "company",
    "company_name": "company",
    "reported_by": "reported_by",
    "assessment_reason": "assessment_reason",
}


def _normalize_date_str(val: str) -> str | None:
    if not val:
        return None
    val = val.strip()
    # YYYY-MM-DD
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", val)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # DD/MM/YYYY or DD-MM-YYYY
    m = re.search(r"\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b", val)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    # Textual month e.g. "27 September 2026"
    month_map = {
        "jan": "01", "january": "01",
        "feb": "02", "february": "02",
        "mar": "03", "march": "03",
        "apr": "04", "april": "04",
        "may": "05",
        "jun": "06", "june": "06",
        "jul": "07", "july": "07",
        "aug": "08", "august": "08",
        "sep": "09", "sept": "09", "september": "09",
        "oct": "10", "october": "10",
        "nov": "11", "november": "11",
        "dec": "12", "december": "12",
    }
    m = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b", val)
    if m and m.group(2).lower() in month_map:
        return f"{m.group(3)}-{month_map[m.group(2).lower()]}-{m.group(1).zfill(2)}"
    m = re.search(r"\b([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})\b", val)
    if m and m.group(1).lower() in month_map:
        return f"{m.group(3)}-{month_map[m.group(1).lower()]}-{m.group(2).zfill(2)}"
    return val


FIELD_LABELS: dict[str, str] = {
    "site": "Site / Plant",
    "site_plant": "Site / Plant",
    "plant": "Site / Plant",
    "facility": "Site / Plant",
    "occurred_on": "Date of Occurrence",
    "date_of_occurrence": "Date of Occurrence",
    "date": "Date of Occurrence",
    "detected_on": "Date Detected",
    "title": "Title / Short Description",
    "title_short_description": "Title / Short Description",
    "short_description": "Title / Short Description",
    "source": "Source Channel",
    "source_channel": "Source Channel",
    "product_name": "Related Product / Material",
    "related_product_material": "Related Product / Material",
    "product": "Related Product / Material",
    "material": "Related Product / Material",
    "product_code": "Product Code",
    "batch_number": "Batch / Lot Number",
    "batch_lot_number": "Batch / Lot Number",
    "batch": "Batch / Lot Number",
    "lot": "Batch / Lot Number",
    "description": "Detailed Description",
    "detailed_description": "Detailed Description",
    "deviation_type": "Deviation Type",
    "impact": "Initial Impact",
    "initial_impact": "Initial Impact",
    "severity": "Initial Severity",
    "initial_severity": "Initial Severity",
    "parameter": "Parameter",
    "expected_condition": "Approved Range",
    "actual_condition": "Actual Value",
    "duration": "Duration",
    "manufacturing_stage": "Manufacturing Stage",
    "equipment": "Equipment",
    "department": "Department",
    "responsible_team": "Responsible Team",
    "immediate_action": "Immediate Action",
    "qa_notified": "QA Notified",
    "batch_status": "Batch Status",
    "company": "Company",
    "reported_by": "Reported By",
    "assessment_reason": "Assessment Reason",
}


def validate_and_normalize_changes(
    changes: dict[str, Any] | list[Any],
    current_form: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> list[FormFieldChange]:
    """Validate each field against the deviation schema, mapping aliases and normalizing values into FormFieldChange."""
    current_form = current_form or {}
    context = context or {}
    validated_list: list[FormFieldChange] = []
    seen_canonical: set[str] = set()

    # Convert dict or list into iterable of (raw_field, raw_val, explicit_label, explicit_old_val)
    items: list[tuple[str, Any, str | None, Any]] = []
    if isinstance(changes, list):
        for item in changes:
            if isinstance(item, FormFieldChange):
                items.append((item.field, item.new_value, item.label, item.old_value))
            elif isinstance(item, dict):
                raw_f = item.get("field") or item.get("name") or item.get("key") or ""
                raw_v = item.get("new_value") if "new_value" in item else item.get("value")
                items.append((str(raw_f), raw_v, item.get("label"), item.get("old_value")))
    elif isinstance(changes, dict):
        for raw_f, raw_v in changes.items():
            if isinstance(raw_v, dict) and "new_value" in raw_v:
                items.append((str(raw_f), raw_v.get("new_value"), raw_v.get("label"), raw_v.get("old_value")))
            else:
                items.append((str(raw_f), raw_v, None, None))

    for raw_k, val, explicit_label, explicit_old in items:
        k = str(raw_k).lower().strip().replace(" ", "_")
        target_field = FIELD_ALIAS_MAP.get(k)
        if not target_field or target_field not in ALLOWED_FORM_FIELDS:
            continue
        if target_field in seen_canonical:
            continue
        seen_canonical.add(target_field)

        # Normalize value
        if target_field in ("occurred_on", "detected_on"):
            norm_date = _normalize_date_str(str(val))
            norm_val = norm_date if norm_date else val
        elif target_field == "qa_notified":
            if isinstance(val, bool):
                norm_val = val
            elif isinstance(val, str):
                norm_val = val.lower().strip() in ("true", "yes", "1")
            else:
                norm_val = bool(val)
        elif target_field in ("deviation_type", "severity", "impact", "batch_status"):
            norm_val = str(val).lower().strip()
        else:
            norm_val = val

        # Determine label
        label = explicit_label or FIELD_LABELS.get(target_field, target_field.replace("_", " ").title())

        # Determine old value from current_form or context
        if explicit_old is not None:
            old_val = explicit_old
        else:
            old_val = (
                current_form.get(target_field)
                or current_form.get(raw_k)
                or context.get(target_field)
                or context.get(raw_k)
                or ""
            )

        # Canonical field identifier (e.g. 'site' for site_plant)
        out_field = "site" if target_field == "site_plant" else target_field

        validated_list.append(
            FormFieldChange(
                field=out_field,
                label=label,
                old_value=old_val if old_val != "" else None,
                new_value=norm_val,
            )
        )

    return validated_list


def _heuristic_update_fallback(
    message: str,
    current_form: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> tuple[str, list[FormFieldChange], str] | None:
    """Parse common natural-language form edit requests for offline/test environments."""
    raw = message.strip()
    lowered = raw.lower()

    # Exclude questions that might start with "what if I change..." or "why did you change"
    if lowered.startswith(("what", "why", "how", "is", "was", "can you tell", "could you explain", "who", "where")):
        return None

    is_update_intent = (
        any(w in lowered for w in ["set ", "change ", "update ", "modify ", "correct "])
        or ("happened on" in lowered or "occurred on" in lowered)
    )

    changes: dict[str, Any] = {}

    # 1. Date of Occurrence ("The incident happened on 27 September 2026 at 10:35 AM")
    m_date = re.search(
        r"(?:happened|occurred|took\s+place|incident\s+date|date)\s+on\s+([^,.]+?)(?:\s+at|\.|$)",
        raw,
        flags=re.IGNORECASE,
    )
    if m_date:
        date_str = m_date.group(1).strip()
        norm_date = _normalize_date_str(date_str)
        if norm_date:
            changes["occurred_on"] = norm_date

    # 2. Description ("Actually, change the description to mention that...")
    m_desc = re.search(
        r"(?:change|update|set)?\s*(?:the\s+)?description\s+(?:to\s+(?:mention\s+that\s+|state\s+that\s+)?|to\s+)(.+)",
        raw,
        flags=re.IGNORECASE,
    )
    if m_desc and "occurred_on" not in changes:
        desc_val = m_desc.group(1).strip().rstrip(".")
        desc_cleaned = re.sub(r"^(?:mention\s+that\s+|say\s+that\s+|state\s+that\s+)", "", desc_val, flags=re.IGNORECASE)
        desc_cleaned = desc_cleaned[0].upper() + desc_cleaned[1:] if desc_cleaned else desc_cleaned
        changes["description"] = desc_cleaned

    # 3. Clauses for all other fields (e.g. 'site to ..., batch to ...', 'product to ...')
    if "description" not in changes:
        cleaned = re.sub(
            r"^(?:actually,?\s*)?(?:please\s+)?(?:set|change|update|modify|correct)\s+(?:the\s+)?",
            "",
            raw,
            flags=re.IGNORECASE,
        ).strip()
        field_keywords = sorted(FIELD_ALIAS_MAP.keys(), key=len, reverse=True)
        clause_pattern = (
            r"(?:(?:and\s+)?(?:the\s+)?("
            + "|".join(re.escape(k) for k in field_keywords)
            + r")\s+(?:to|=|is)\s+([^,]+?))(?=(?:,\s*(?:and\s+)?|\s+and\s+|$|\.))"
        )
        for m in re.finditer(clause_pattern, cleaned, flags=re.IGNORECASE):
            f_name = m.group(1).lower().strip()
            val = m.group(2).strip().rstrip(".")
            canonical = FIELD_ALIAS_MAP.get(f_name)
            if canonical and canonical not in changes:
                changes[canonical] = val

    if not changes:
        if is_update_intent:
            return (
                "answer_question",
                [],
                "I couldn't determine which form field you want to change. Please specify the information you want to update.",
            )
        return None

    structured_changes = validate_and_normalize_changes(
        changes,
        current_form=current_form,
        context=context,
    )
    if not structured_changes:
        if is_update_intent:
            return (
                "answer_question",
                [],
                "I couldn't determine which form field you want to change. Please specify the information you want to update.",
            )
        return None

    count = len(structured_changes)
    confirm_msg = "Change applied." if count == 1 else f"{count} changes applied."
    return "update_form", structured_changes, confirm_msg


def _heuristic_chat_fallback(
    message: str,
    context: dict[str, Any],
    assessment: dict[str, Any] | None,
    current_form: dict[str, Any],
    raw_content: str | None,
) -> tuple[str, str, list[FormFieldChange]]:
    """Deterministic, grounded rule-based answer and update generator for offline/test environments.

    Returns tuple of (intent, response_message, changes_list).
    """
    # 1. Check if user is asking to update form fields
    update_res = _heuristic_update_fallback(message, current_form=current_form, context=context)
    if update_res is not None:
        intent, changes, confirm_msg = update_res
        return intent, confirm_msg, changes

    msg = message.lower().strip()
    assessment = assessment or {}
    context = context or {}
    current_form = current_form or {}

    rec_sev = assessment.get("recommended_severity") or assessment.get("severity")
    rec_imp = assessment.get("recommended_impact") or assessment.get("impact")
    rec_reason = assessment.get("reason") or assessment.get("severity_reason") or assessment.get("impact_reason")

    form_sev = current_form.get("severity")
    form_imp = current_form.get("impact")

    batch = (
        context.get("batch_lot_number")
        or current_form.get("batch_number")
        or context.get("batch_number")
    )
    product = (
        context.get("related_product_material")
        or current_form.get("product_name")
        or context.get("product_name")
    )
    equipment = (
        context.get("equipment")
        or current_form.get("equipment")
    )
    actual_val = (
        context.get("actual_value")
        or current_form.get("actual_condition")
    )
    approved_range = (
        context.get("approved_range")
        or current_form.get("expected_condition")
    )
    duration = (
        context.get("duration")
        or current_form.get("duration")
    )
    action = (
        context.get("immediate_action")
        or current_form.get("immediate_action")
    )
    qa_notified = context.get("qa_notified")
    if qa_notified is None:
        qa_notified = current_form.get("qa_notified")

    missing_fields = context.get("missing_information") or []

    # Check for unavailable severity
    if any(k in msg for k in ["severity", "critical", "major", "minor"]) and "assessment" in msg and not rec_sev:
        return "answer_question", "The AI severity assessment is currently unavailable. A qualified reviewer must evaluate the deviation and determine the severity.", []

    # Form severity vs recommended severity distinction
    if ("form" in msg or "override" in msg or "change" in msg) and ("severity" in msg):
        if form_sev and rec_sev and str(form_sev).lower() != str(rec_sev).lower():
            ans = (
                f"The current severity on the form is set to {form_sev.capitalize()}, "
                f"whereas the initial AI recommendation was {rec_sev.capitalize()}"
                + (f" due to: {rec_reason}" if rec_reason else ".")
            )
            return "answer_question", ans, []
        elif form_sev:
            return "answer_question", f"The current severity on the form is {form_sev.capitalize()}.", []

    # Why critical / why major / severity questions
    if "why" in msg and ("critical" in msg or "major" in msg or "minor" in msg):
        if rec_sev:
            return "answer_question", f"This deviation was evaluated as {rec_sev.capitalize()} because {rec_reason or 'it compromises critical quality attributes or specifications'}.", []
        return "answer_question", "The AI severity assessment is currently unavailable. A qualified reviewer must evaluate the deviation and determine the severity.", []

    if "severity" in msg:
        if not rec_sev:
            return "answer_question", "The AI severity assessment is currently unavailable. A qualified reviewer must evaluate the deviation and determine the severity.", []
        return "answer_question", f"The recommended severity is {rec_sev.capitalize()}." + (f" Reason: {rec_reason}" if rec_reason else ""), []

    # Impact questions
    if "impact" in msg:
        if rec_imp:
            imp_display = str(rec_imp).replace("_", " ").title()
            return "answer_question", f"The evaluated impact area is {imp_display}." + (f" Justification: {rec_reason}" if rec_reason else ""), []
        return "answer_question", "The provided deviation information does not contain enough information to answer that.", []

    # Within approved range question
    if ("within" in msg or "in range" in msg or "exceed" in msg or "below" in msg) and ("range" in msg or "approved" in msg or "limit" in msg or "spec" in msg):
        if actual_val and approved_range:
            return "answer_question", f"No, the actual value ({actual_val}) was outside the approved range ({approved_range}).", []
        return "answer_question", "The provided deviation information does not contain enough information to answer that.", []

    # Actual temperature / value
    if "actual" in msg or ("temperature" in msg and "what" in msg):
        if actual_val:
            return "answer_question", f"The actual value recorded was {actual_val}.", []
        return "answer_question", "The provided deviation information does not contain enough information to answer that.", []

    # Approved range / limit
    if "approved range" in msg or "limit" in msg or ("range" in msg and "what" in msg):
        if approved_range:
            return "answer_question", f"The approved range is {approved_range}.", []
        return "answer_question", "The provided deviation information does not contain enough information to answer that.", []

    # Batch / lot
    if "batch" in msg or "lot" in msg:
        if "current batch" in msg:
            if batch:
                return "answer_question", f"The current batch number is {batch}.", []
        elif batch:
            return "answer_question", f"Batch {batch} was affected.", []
        return "answer_question", "The provided deviation information does not contain enough information to answer that.", []

    # Equipment / machine
    if "equipment" in msg or "machine" in msg or "autoclave" in msg:
        if equipment:
            return "answer_question", f"The equipment involved was {equipment}.", []
        return "answer_question", "The provided deviation information does not contain enough information to answer that.", []

    # Product / material
    if "product" in msg or "material" in msg:
        if product:
            return "answer_question", f"The related product is {product}.", []
        return "answer_question", "The provided deviation information does not contain enough information to answer that.", []

    # Excursion duration
    if "duration" in msg or "how long" in msg:
        if duration:
            return "answer_question", f"The duration of the excursion was {duration}.", []
        return "answer_question", "The provided deviation information does not contain enough information to answer that.", []

    # Immediate action taken
    if "immediate action" in msg or "action taken" in msg or "containment" in msg:
        if action:
            return "answer_question", f"The immediate action taken was: {action}.", []
        return "answer_question", "The provided deviation information does not contain enough information to answer that.", []

    # QA notification
    if "qa" in msg and ("notified" in msg or "notification" in msg or "inform" in msg):
        if qa_notified is True:
            return "answer_question", "Yes, QA was notified.", []
        elif qa_notified is False:
            return "answer_question", "No, QA was not notified.", []
        return "answer_question", "The provided deviation information does not contain enough information to answer that.", []

    # Missing information
    if "missing" in msg:
        if missing_fields:
            return "answer_question", f"The following fields were identified as missing from the provided input: {', '.join(missing_fields)}.", []
        return "answer_question", "No standard deviation fields were identified as missing.", []

    # Summarize / summary
    if "summarize" in msg or "summary" in msg or "what happened" in msg:
        title = context.get("title_short_description") or current_form.get("title")
        desc = context.get("detailed_description") or current_form.get("description")
        parts = []
        if title:
            parts.append(title)
        if equipment and equipment not in (title or ""):
            parts.append(f"Involving {equipment}")
        if batch and batch not in (title or ""):
            parts.append(f"affecting batch {batch}")
        if actual_val:
            parts.append(f"where actual value reached {actual_val}")
        if approved_range:
            parts.append(f"(approved limit: {approved_range})")
        if action:
            parts.append(f"Immediate action: {action}")
        if parts:
            return "answer_question", ". ".join(parts) + ".", []
        elif desc:
            return "answer_question", desc[:250] + "...", []

    # If question asks about things not present in the content
    return "answer_question", "The provided deviation information does not contain enough information to answer that.", []


async def answer_deviation_chat(payload: DeviationChatRequest) -> DeviationChatResponse:
    """Answer questions or execute structured form updates using Groq or safe fallback."""
    raw_content = payload.raw_content or ""
    context = payload.context or {}
    assessment = payload.assessment or {}
    current_form = payload.current_form or {}
    message = payload.message.strip()

    context_prompt = (
        f"[DEVIATION CONTEXT]\n"
        f"Raw Source Text:\n{raw_content}\n\n"
        f"Extracted Structured Fields:\n{json.dumps(context, indent=2)}\n\n"
        f"AI Assessment Recommendation:\n{json.dumps(assessment, indent=2)}\n\n"
        f"Current Form Values (user-edited):\n{json.dumps(current_form, indent=2)}\n\n"
        f"[USER MESSAGE]\n{message}"
    )

    try:
        client, model = _get_groq_client()
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": DEVIATION_CHAT_SYSTEM_PROMPT},
                {"role": "user", "content": context_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1024,
        )
        content = (response.choices[0].message.content or "").strip()
        if content:
            try:
                parsed = json.loads(content)
                intent = parsed.get("intent", "answer_question")
                raw_changes = parsed.get("changes", [])
                msg = parsed.get("message") or parsed.get("response", "")

                validated_changes = validate_and_normalize_changes(
                    raw_changes,
                    current_form=current_form,
                    context=context,
                )
                if intent == "update_form":
                    if not validated_changes:
                        intent = "answer_question"
                        msg = "I couldn't determine which form field you want to change. Please specify the information you want to update."
                    else:
                        count = len(validated_changes)
                        msg = "Change applied." if count == 1 else f"{count} changes applied."

                return DeviationChatResponse(
                    response=msg,
                    intent=intent,
                    changes=validated_changes,
                    message=msg,
                )
            except Exception as parse_err:
                logger.warning("Could not parse Groq JSON response (%s): %s", parse_err, content)
                return DeviationChatResponse(response=content, message=content)
    except Exception as exc:
        logger.warning("Groq deviation chat failed (%s). Using grounded fallback responder.", exc)

    # Grounded heuristic fallback
    intent, fallback_text, fallback_changes = _heuristic_chat_fallback(
        message=message,
        context=context,
        assessment=assessment,
        current_form=current_form,
        raw_content=raw_content,
    )
    return DeviationChatResponse(
        response=fallback_text,
        intent=intent,
        changes=fallback_changes,
        message=fallback_text,
    )


from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import (
    BatchStatus,
    DeviationSource,
    DeviationStatus,
    DeviationType,
    Impact,
    Severity,
)


class DeviationBase(BaseModel):
    """Shared deviation fields, supporting both AIVOA canonical naming and database attributes."""

    # Identification
    source: DeviationSource = DeviationSource.MANUAL
    site_plant: str | None = Field(default=None, max_length=160, description="Manufacturing site / facility")
    reported_by: str | None = Field(default=None, max_length=120)
    occurred_on: date | None = None
    date_of_occurrence: date | None = None
    detected_on: date | None = None

    # Organization
    company: str | None = Field(default=None, max_length=160, description="Company name")
    company_name: str | None = Field(default=None, max_length=160, description="Company name")
    company_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    department: str | None = Field(default=None, max_length=120)
    responsible_team: str | None = Field(default=None, max_length=120)

    # Product
    product_name: str | None = Field(default=None, max_length=200)
    related_product_material: str | None = Field(default=None, max_length=200)
    product_code: str | None = Field(default=None, max_length=120)
    batch_number: str | None = Field(default=None, max_length=120)
    batch_lot_number: str | None = Field(default=None, max_length=120)

    # Event
    manufacturing_stage: str | None = Field(default=None, max_length=160)
    process_operation: str | None = Field(default=None, max_length=160)
    equipment: str | None = Field(default=None, max_length=160)
    title: str | None = Field(default=None, max_length=255)
    title_short_description: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None)
    detailed_description: str | None = Field(default=None)
    deviation_type: DeviationType

    # Conditions & Parameters
    expected_condition: str | None = None
    approved_range: str | None = None
    actual_condition: str | None = None
    actual_value: str | None = None
    duration: str | None = Field(default=None, max_length=120)
    parameter: str | None = Field(default=None, max_length=160)

    # Immediate response
    immediate_action: str | None = None
    batch_status: BatchStatus | None = None
    qa_notified: bool | None = None

    # Assessment (final, user-reviewed authoritative values)
    impact: Impact | None = None
    initial_impact: Impact | None = None
    severity: Severity | None = None
    initial_severity: Severity | None = None
    assessment_reason: str | None = None

    # Traceability of original AI proposals
    ai_recommended_impact: str | None = None
    ai_recommended_severity: str | None = None
    ai_reason: str | None = None
    ai_evidence: list[Any] | dict | None = None

    # Connected QMS Workflow Relationships
    batch_id: uuid.UUID | None = None
    manufacturing_step_id: uuid.UUID | None = None
    in_process_check_id: uuid.UUID | None = None
    workflow_status: str | None = None
    closed_at: datetime | None = None
    closed_by: str | None = None
    closure_reason: str | None = None
    closure_summary: str | None = None
    effectiveness_result: str | None = None

    @model_validator(mode="before")
    @classmethod
    def sync_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Title
            title = data.get("title") or data.get("title_short_description")
            if title:
                data.setdefault("title", title)
                data.setdefault("title_short_description", title)
            # Description
            desc = data.get("description") or data.get("detailed_description")
            if desc:
                data.setdefault("description", desc)
                data.setdefault("detailed_description", desc)
            # Product
            prod = data.get("product_name") or data.get("related_product_material")
            if prod:
                data.setdefault("product_name", prod)
                data.setdefault("related_product_material", prod)
            # Batch
            batch = data.get("batch_number") or data.get("batch_lot_number")
            if batch:
                data.setdefault("batch_number", batch)
                data.setdefault("batch_lot_number", batch)
            # Date
            dt = data.get("occurred_on") or data.get("date_of_occurrence")
            if dt:
                data.setdefault("occurred_on", dt)
                data.setdefault("date_of_occurrence", dt)
            # Conditions
            exp = data.get("expected_condition") or data.get("approved_range")
            if exp:
                data.setdefault("expected_condition", exp)
                data.setdefault("approved_range", exp)
            act = data.get("actual_condition") or data.get("actual_value")
            if act:
                data.setdefault("actual_condition", act)
                data.setdefault("actual_value", act)
            # Impact
            imp = data.get("impact") or data.get("initial_impact")
            if imp:
                data.setdefault("impact", imp)
                data.setdefault("initial_impact", imp)
            # Severity
            sev = data.get("severity") or data.get("initial_severity")
            if sev:
                data.setdefault("severity", sev)
                data.setdefault("initial_severity", sev)
            # Company
            comp = data.get("company") or data.get("company_name")
            if comp:
                data.setdefault("company", comp)
                data.setdefault("company_name", comp)

            # Deviation type normalization
            dev_type = data.get("deviation_type")
            if isinstance(dev_type, str) and dev_type.strip():
                clean_type = dev_type.strip().lower()
                if "process" in clean_type:
                    clean_type = "process"
                data["deviation_type"] = clean_type

            # Source normalization
            src = data.get("source")
            if isinstance(src, str) and src.strip():
                clean_src = src.strip().lower()
                if "manufacturing" in clean_src or "ipc" in clean_src:
                    clean_src = "manufacturing"
                data["source"] = clean_src

            # Date normalization and empty-string cleanup
            for dt_k in ("occurred_on", "date_of_occurrence", "detected_on"):
                val = data.get(dt_k)
                if val == "":
                    data[dt_k] = None
        return data

    @model_validator(mode="after")
    def validate_required_fields(self) -> DeviationBase:
        # Title must be at least 3 characters
        resolved_title = self.title or self.title_short_description
        if not resolved_title or len(resolved_title.strip()) < 3:
            raise ValueError("title (or title_short_description) must be at least 3 characters.")
        self.title = resolved_title.strip()
        self.title_short_description = resolved_title.strip()

        # Description must be at least 10 characters
        resolved_desc = self.description or self.detailed_description
        if not resolved_desc or len(resolved_desc.strip()) < 10:
            raise ValueError("description (or detailed_description) must be at least 10 characters.")
        self.description = resolved_desc.strip()
        self.detailed_description = resolved_desc.strip()

        # Sync secondary aliases
        if self.product_name and not self.related_product_material:
            self.related_product_material = self.product_name
        if self.batch_number and not self.batch_lot_number:
            self.batch_lot_number = self.batch_number
        if self.occurred_on and not self.date_of_occurrence:
            self.date_of_occurrence = self.occurred_on
        if self.expected_condition and not self.approved_range:
            self.approved_range = self.expected_condition
        if self.actual_condition and not self.actual_value:
            self.actual_value = self.actual_condition
        if self.impact and not self.initial_impact:
            self.initial_impact = self.impact
        if self.severity and not self.initial_severity:
            self.initial_severity = self.severity

        return self


class DeviationCreate(DeviationBase):
    """Payload to save a final, user-reviewed deviation with AI audit snapshots."""

    ai_extraction: dict | None = None
    ai_assessment: dict | None = None


class DeviationUpdate(BaseModel):
    """Full/partial update of a reviewed deviation. All fields optional."""

    source: DeviationSource | None = None
    site_plant: str | None = Field(default=None, max_length=160)
    reported_by: str | None = Field(default=None, max_length=120)
    occurred_on: date | None = None
    date_of_occurrence: date | None = None
    detected_on: date | None = None
    company_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    department: str | None = Field(default=None, max_length=120)
    responsible_team: str | None = Field(default=None, max_length=120)
    product_name: str | None = Field(default=None, max_length=200)
    related_product_material: str | None = Field(default=None, max_length=200)
    product_code: str | None = Field(default=None, max_length=120)
    batch_number: str | None = Field(default=None, max_length=120)
    batch_lot_number: str | None = Field(default=None, max_length=120)
    manufacturing_stage: str | None = Field(default=None, max_length=160)
    process_operation: str | None = Field(default=None, max_length=160)
    equipment: str | None = Field(default=None, max_length=160)
    title: str | None = Field(default=None, min_length=3, max_length=255)
    title_short_description: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=10)
    detailed_description: str | None = Field(default=None, min_length=10)
    deviation_type: DeviationType | None = None
    expected_condition: str | None = None
    approved_range: str | None = None
    actual_condition: str | None = None
    actual_value: str | None = None
    duration: str | None = Field(default=None, max_length=120)
    parameter: str | None = Field(default=None, max_length=160)
    immediate_action: str | None = None
    batch_status: BatchStatus | None = None
    qa_notified: bool | None = None
    impact: Impact | None = None
    initial_impact: Impact | None = None
    severity: Severity | None = None
    initial_severity: Severity | None = None
    assessment_reason: str | None = None
    status: DeviationStatus | None = None
    ai_extraction: dict | None = None
    ai_assessment: dict | None = None
    ai_recommended_impact: str | None = None
    ai_recommended_severity: str | None = None
    ai_reason: str | None = None
    ai_evidence: list[Any] | dict | None = None
    batch_id: uuid.UUID | None = None
    manufacturing_step_id: uuid.UUID | None = None
    in_process_check_id: uuid.UUID | None = None
    workflow_status: str | None = None
    closed_at: datetime | None = None
    closed_by: str | None = None
    closure_reason: str | None = None
    closure_summary: str | None = None
    effectiveness_result: str | None = None


class DeviationRead(DeviationBase):
    """Complete deviation record returned by API, confirming persistent database save."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    status: DeviationStatus
    success: bool = True
    ai_extraction: dict | None = None
    ai_assessment: dict | None = None
    created_at: datetime
    updated_at: datetime
    investigation_id: uuid.UUID | None = None
    investigation_reference: str | None = None
    capa_id: uuid.UUID | None = None
    capa_reference: str | None = None


class DeviationList(BaseModel):
    items: list[DeviationRead]
    total: int
    limit: int
    offset: int

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import (
    BatchStatus,
    DeviationSource,
    DeviationStatus,
    DeviationType,
    Impact,
    Severity,
)


class DeviationBase(BaseModel):
    """Shared deviation fields, grouped to match the Log Deviation form."""

    # Identification
    source: DeviationSource = DeviationSource.MANUAL
    reported_by: str | None = Field(default=None, max_length=120)
    occurred_on: date | None = None
    detected_on: date | None = None

    # Organization
    company_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    department: str | None = Field(default=None, max_length=120)
    responsible_team: str | None = Field(default=None, max_length=120)

    # Product
    product_name: str | None = Field(default=None, max_length=200)
    product_code: str | None = Field(default=None, max_length=120)
    batch_number: str | None = Field(default=None, max_length=120)

    # Event
    manufacturing_stage: str | None = Field(default=None, max_length=160)
    equipment: str | None = Field(default=None, max_length=160)
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    deviation_type: DeviationType

    # Conditions
    expected_condition: str | None = None
    actual_condition: str | None = None
    duration: str | None = Field(default=None, max_length=120)
    parameter: str | None = Field(default=None, max_length=160)

    # Immediate response
    immediate_action: str | None = None
    batch_status: BatchStatus | None = None
    qa_notified: bool | None = None

    # Assessment (final, user-reviewed)
    impact: Impact | None = None
    severity: Severity | None = None
    assessment_reason: str | None = None


class DeviationCreate(DeviationBase):
    """Payload to save a final, user-reviewed deviation.

    Optional AI snapshots can be attached for audit (what the assistant
    proposed vs. what the user saved).
    """

    ai_extraction: dict | None = None
    ai_assessment: dict | None = None


class DeviationUpdate(BaseModel):
    """Full/partial update of a reviewed deviation. All fields optional."""

    source: DeviationSource | None = None
    reported_by: str | None = Field(default=None, max_length=120)
    occurred_on: date | None = None
    detected_on: date | None = None
    company_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    department: str | None = Field(default=None, max_length=120)
    responsible_team: str | None = Field(default=None, max_length=120)
    product_name: str | None = Field(default=None, max_length=200)
    product_code: str | None = Field(default=None, max_length=120)
    batch_number: str | None = Field(default=None, max_length=120)
    manufacturing_stage: str | None = Field(default=None, max_length=160)
    equipment: str | None = Field(default=None, max_length=160)
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=10)
    deviation_type: DeviationType | None = None
    expected_condition: str | None = None
    actual_condition: str | None = None
    duration: str | None = Field(default=None, max_length=120)
    parameter: str | None = Field(default=None, max_length=160)
    immediate_action: str | None = None
    batch_status: BatchStatus | None = None
    qa_notified: bool | None = None
    impact: Impact | None = None
    severity: Severity | None = None
    assessment_reason: str | None = None
    status: DeviationStatus | None = None
    ai_extraction: dict | None = None
    ai_assessment: dict | None = None


class DeviationRead(DeviationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    status: DeviationStatus
    ai_extraction: dict | None
    ai_assessment: dict | None
    created_at: datetime
    updated_at: datetime


class DeviationList(BaseModel):
    items: list[DeviationRead]
    total: int
    limit: int
    offset: int

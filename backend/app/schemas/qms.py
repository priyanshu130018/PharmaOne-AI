from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


# ------------------------------------------------------------------------------
# Manufacturing Steps & In-Process Checks
# ------------------------------------------------------------------------------

class ManufacturingStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    batch_id: uuid.UUID
    step_number: int
    name: str
    status: str
    warning_details: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ManufacturingStepCreate(BaseModel):
    step_number: Optional[int] = None
    name: str
    status: str = "pending"  # pending, in_progress, completed, warning
    warning_details: Optional[str] = None


class InProcessCheckCreate(BaseModel):
    parameter: str
    specification: str
    actual_value: str
    status: Optional[str] = None  # auto-determined if not supplied: "Within Limit" | "OUT-OF-LIMIT (OOL)"
    step_id: Optional[uuid.UUID] = None
    step_number: Optional[int] = None
    operator: Optional[str] = None
    notes: Optional[str] = None
    deviation_id: Optional[uuid.UUID] = None
    spec_min: Optional[float] = None
    spec_max: Optional[float] = None
    unit: Optional[str] = None
    check_time: Optional[str] = None


class InProcessCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    batch_id: uuid.UUID
    step_id: Optional[uuid.UUID] = None
    company_id: uuid.UUID
    parameter: str
    specification: str
    actual_value: str
    status: str
    checked_at: datetime
    checked_by: Optional[str] = None
    notes: Optional[str] = None
    deviation_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


# ------------------------------------------------------------------------------
# Raw Materials & Suppliers
# ------------------------------------------------------------------------------

class SupplierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    code: Optional[str] = None
    status: str
    risk_level: str
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def supplier_name(self) -> str:
        return self.name

    @computed_field
    @property
    def supplier_code(self) -> Optional[str]:
        return self.code


class RawMaterialCreate(BaseModel):
    name: str
    material_code: Optional[str] = None
    lot_number: str
    supplier_id: Optional[uuid.UUID] = None
    supplier_name: Optional[str] = None
    batch_id: Optional[Union[uuid.UUID, str]] = None
    status: str = "Approved"


class RawMaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    supplier_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    name: str
    material_code: Optional[str] = None
    lot_number: str
    status: str
    supplier_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def material_name(self) -> str:
        return self.name


# ------------------------------------------------------------------------------
# Batches
# ------------------------------------------------------------------------------

class BatchCreate(BaseModel):
    batch_number: str
    product_name: str
    product_code: Optional[str] = None
    recipe_version: str = "v1.0"
    site_plant: str = "Bengaluru"
    equipment: Optional[str] = "Reactor 2"
    planned_date: Optional[str] = None
    status: str = "In Progress"
    release_status: str = "Pending"
    manufacturing_date: Optional[str] = None
    started_at: Optional[datetime] = None
    raw_material_lot_numbers: Optional[List[str]] = None


class BatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    site_id: Optional[uuid.UUID] = None
    batch_number: str
    product_name: str
    product_code: Optional[str] = None
    recipe_version: str
    site_plant: str
    equipment: Optional[str] = "Reactor 2"
    status: str
    release_status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class BatchDetail(BatchRead):
    manufacturing_steps: List[ManufacturingStepRead] = []
    in_process_checks: List[InProcessCheckRead] = []
    raw_materials: List[RawMaterialRead] = []
    linked_deviation_references: List[str] = []
    linked_investigation_references: List[str] = []
    linked_capa_references: List[str] = []
    batch_release_status: Optional[str] = None
    batch_release_id: Optional[uuid.UUID] = None


class DeviationSeverityConfirm(BaseModel):
    severity: str
    impact: Optional[str] = None
    decision: str = "Accept"  # Accept | Edit | Reject
    notes: Optional[str] = None
    confirmed_by: Optional[str] = None



class BatchList(BaseModel):
    items: List[BatchRead]
    total: int


# ------------------------------------------------------------------------------
# Investigation Tasks & Evidence
# ------------------------------------------------------------------------------

class InvestigationTaskCreate(BaseModel):
    task_number: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    owner: str = "QA"
    status: str = "Pending"  # Pending, In Progress, Completed
    due_date: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def sync_title_desc(cls, data: Any) -> Any:
        if isinstance(data, dict):
            t = data.get("title") or data.get("description") or "Investigation Task"
            data["title"] = t
            data.setdefault("description", t)
        return data


class InvestigationTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None
    notes: Optional[str] = None
    completed_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def sync_update_title(cls, data: Any) -> Any:
        if isinstance(data, dict):
            t = data.get("title") or data.get("description")
            if t:
                data["title"] = t
        return data


class InvestigationTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    investigation_id: uuid.UUID
    task_number: int
    title: str
    owner: str
    status: str
    due_date: Optional[str] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    @computed_field
    @property
    def description(self) -> str:
        return self.title


class InvestigationEvidenceCreate(BaseModel):
    title: str
    evidence_type: str = "document"  # log, maintenance, sop, document
    reference_doc: Optional[str] = None
    snippet: Optional[str] = None
    summary: Optional[str] = None
    attached_by: Optional[str] = None
    meta: Optional[dict] = None

    @model_validator(mode="before")
    @classmethod
    def sync_snippet_summary(cls, data: Any) -> Any:
        if isinstance(data, dict):
            s = data.get("snippet") or data.get("summary")
            if s:
                data["snippet"] = s
                data.setdefault("summary", s)
        return data


class InvestigationEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    investigation_id: uuid.UUID
    title: str
    evidence_type: str
    reference_doc: Optional[str] = None
    snippet: Optional[str] = None
    attached_by: Optional[str] = None
    meta: Optional[dict] = None
    created_at: datetime

    @computed_field
    @property
    def summary(self) -> Optional[str]:
        return self.snippet


# ------------------------------------------------------------------------------
# Root Cause Analysis
# ------------------------------------------------------------------------------

class RootCauseAnalysisCreate(BaseModel):
    problem_statement: str
    why_1: str
    why_2: Optional[str] = None
    why_3: Optional[str] = None
    why_4: Optional[str] = None
    why_5: Optional[str] = None
    root_cause_summary: str
    category: str = "Equipment / Maintenance"
    contributing_factors: Optional[str] = None
    is_confirmed: bool = False
    confirmed_by: Optional[str] = None
    ai_draft: Optional[dict] = None


class RootCauseAnalysisUpdate(BaseModel):
    problem_statement: Optional[str] = None
    why_1: Optional[str] = None
    why_2: Optional[str] = None
    why_3: Optional[str] = None
    why_4: Optional[str] = None
    why_5: Optional[str] = None
    root_cause_summary: Optional[str] = None
    category: Optional[str] = None
    contributing_factors: Optional[str] = None
    is_confirmed: Optional[bool] = None
    confirmed_by: Optional[str] = None


class RootCauseConfirmRequest(BaseModel):
    problem_statement: str
    why_1: str
    why_2: Optional[str] = None
    why_3: Optional[str] = None
    why_4: Optional[str] = None
    why_5: Optional[str] = None
    root_cause_summary: Optional[str] = None
    final_root_cause: Optional[str] = None
    category: Optional[str] = "Equipment / Maintenance"
    contributing_factors: Optional[Any] = None
    confirmed_by: Optional[str] = None
    human_confirmed: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def sync_rc_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            rc = data.get("root_cause_summary") or data.get("final_root_cause") or ""
            data["root_cause_summary"] = rc
            data.setdefault("final_root_cause", rc)
            cf = data.get("contributing_factors")
            if isinstance(cf, list):
                data["contributing_factors"] = ", ".join(str(x) for x in cf)
        return data


class RootCauseAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    investigation_id: uuid.UUID
    deviation_id: uuid.UUID
    company_id: uuid.UUID
    problem_statement: str
    why_1: str
    why_2: Optional[str] = None
    why_3: Optional[str] = None
    why_4: Optional[str] = None
    why_5: Optional[str] = None
    root_cause_summary: str
    category: str
    contributing_factors: Optional[str] = None
    is_confirmed: bool
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    ai_draft: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def final_root_cause(self) -> str:
        return self.root_cause_summary


# ------------------------------------------------------------------------------
# Investigations
# ------------------------------------------------------------------------------

class InvestigationCreate(BaseModel):
    deviation_id: uuid.UUID
    title: Optional[str] = None
    lead_investigator: Optional[str] = None
    overview: Optional[str] = None
    investigation_plan: Optional[str] = None
    methodology: Optional[str] = "Root Cause Analysis & 5 Whys"


class InvestigationCompleteRequest(BaseModel):
    conclusion: str
    completed_by: Optional[str] = None
    product_impact_assessment: Optional[str] = None


class InvestigationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    deviation_id: uuid.UUID
    company_id: uuid.UUID
    title: str
    status: str
    lead_investigator: str
    overview: Optional[str] = None
    investigation_plan: Optional[str] = None
    methodology: Optional[str] = None
    conclusion: Optional[str] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    tasks: List[InvestigationTaskRead] = []
    evidence: List[InvestigationEvidenceRead] = []
    root_cause: Optional[RootCauseAnalysisRead] = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def root_cause_analysis(self) -> Optional[RootCauseAnalysisRead]:
        return self.root_cause


# ------------------------------------------------------------------------------
# CAPA & CAPA Actions
# ------------------------------------------------------------------------------

class CapaActionCreate(BaseModel):
    action_type: str = "CORRECTIVE"  # "CORRECTIVE" | "PREVENTIVE"
    action_description: Optional[str] = None
    description: Optional[str] = None
    owner: str = "Engineering"
    due_date: Optional[str] = "2026-10-15"
    status: str = "Pending"  # Pending, In Progress, Completed
    evidence_reference: Optional[str] = None
    verification_plan: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def sync_action_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            desc = data.get("action_description") or data.get("description") or "Remediation action item"
            data["action_description"] = desc
            data.setdefault("description", desc)
            if not data.get("due_date"):
                data["due_date"] = "2026-10-15"
            ev = data.get("evidence_reference") or data.get("verification_plan")
            if ev:
                data["evidence_reference"] = ev
                data.setdefault("verification_plan", ev)
            at = data.get("action_type") or "CORRECTIVE"
            data["action_type"] = at.upper()
        return data


class CapaActionUpdate(BaseModel):
    action_description: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None
    evidence_reference: Optional[str] = None
    completed_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def sync_update_desc(cls, data: Any) -> Any:
        if isinstance(data, dict):
            desc = data.get("action_description") or data.get("description")
            if desc:
                data["action_description"] = desc
        return data


class CapaActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    capa_id: uuid.UUID
    action_type: str
    action_description: str
    owner: str
    due_date: str
    status: str
    evidence_reference: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    @computed_field
    @property
    def description(self) -> str:
        return self.action_description


# ------------------------------------------------------------------------------
# Effectiveness Checks
# ------------------------------------------------------------------------------

class EffectivenessCheckCreate(BaseModel):
    capa_id: uuid.UUID
    deviation_id: uuid.UUID
    plan_description: str = "Monitor the next five batches with no recurrence"
    criteria: str = "Zero temperature excursions during reaction phase"
    monitored_batches: Optional[List[dict]] = None


class EffectivenessCheckReviewRequest(BaseModel):
    status: Optional[str] = None
    result: Optional[str] = None
    comments: Optional[str] = None
    summary: Optional[str] = None
    reviewed_by: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def sync_eff_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            st = data.get("status") or data.get("result") or "effective"
            data["status"] = st.lower()
            data.setdefault("result", st)
            c = data.get("comments") or data.get("summary")
            if c:
                data["comments"] = c
                data.setdefault("summary", c)
        return data


class EffectivenessCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    capa_id: uuid.UUID
    deviation_id: uuid.UUID
    company_id: uuid.UUID
    plan_description: str
    criteria: str
    monitored_batches: Optional[List[dict]] = None
    ai_summary: Optional[str] = None
    status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    comments: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def result(self) -> str:
        return self.status.capitalize()

    @computed_field
    @property
    def summary(self) -> Optional[str]:
        return self.comments or self.plan_description


# ------------------------------------------------------------------------------
# CAPA
# ------------------------------------------------------------------------------

class CapaCreate(BaseModel):
    deviation_id: uuid.UUID
    investigation_id: Optional[uuid.UUID] = None
    root_cause_id: Optional[uuid.UUID] = None
    title: str
    root_cause_summary: str
    target_completion_date: Optional[date] = None
    actions: Optional[List[CapaActionCreate]] = None


class CapaUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    root_cause_summary: Optional[str] = None
    target_completion_date: Optional[date] = None


class CapaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    deviation_id: uuid.UUID
    investigation_id: Optional[uuid.UUID] = None
    root_cause_id: Optional[uuid.UUID] = None
    company_id: uuid.UUID
    title: str
    root_cause_summary: str
    status: str
    created_by: str
    target_completion_date: Optional[date] = None
    actions: List[CapaActionRead] = []
    effectiveness_check: Optional[EffectivenessCheckRead] = None
    created_at: datetime
    updated_at: datetime


# ------------------------------------------------------------------------------
# Deviation Closure
# ------------------------------------------------------------------------------

class DeviationCloseRequest(BaseModel):
    closure_reason: str
    closure_summary: Optional[str] = None
    reviewer_name: Optional[str] = None


# ------------------------------------------------------------------------------
# Batch Release
# ------------------------------------------------------------------------------

class BatchReleaseDecisionRequest(BaseModel):
    decision: Optional[str] = None
    disposition: Optional[str] = None
    rationale: str
    checklist_review: Optional[dict] = None
    decided_by: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def sync_decision(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = data.get("decision") or data.get("disposition") or "RELEASED"
            data["decision"] = d.upper()
            data.setdefault("disposition", d)
        return data


class BatchReleaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    batch_id: uuid.UUID
    company_id: uuid.UUID
    status: str
    decision_rationale: Optional[str] = None
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    checklist_review: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def disposition(self) -> str:
        return self.status.capitalize()

    @computed_field
    @property
    def rationale(self) -> Optional[str]:
        return self.decision_rationale


# ------------------------------------------------------------------------------
# Complaints
# ------------------------------------------------------------------------------

class ComplaintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    company_id: uuid.UUID
    batch_id: Optional[uuid.UUID] = None
    deviation_id: Optional[uuid.UUID] = None
    product_name: str
    description: str
    potential_impact: str
    recall_assessment: str
    status: str
    batch_number: Optional[str] = None
    deviation_reference: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def complaint_number(self) -> str:
        return self.reference

    @computed_field
    @property
    def issue_description(self) -> str:
        return self.description

    @computed_field
    @property
    def deviation_number(self) -> Optional[str]:
        return self.deviation_reference

    @computed_field
    @property
    def investigation_number(self) -> str:
        return "INV-2026-012"


# ------------------------------------------------------------------------------
# Linked Records
# ------------------------------------------------------------------------------

class LinkedRecordItem(BaseModel):
    record_type: str
    id: Optional[str] = None
    reference: str
    title: str
    status: str
    badge_color: str = "blue"
    url_target: str


class LinkedRecordsResponse(BaseModel):
    deviation_reference: str
    batch: Optional[LinkedRecordItem] = None
    ipc: Optional[LinkedRecordItem] = None
    investigation: Optional[LinkedRecordItem] = None
    root_cause: Optional[LinkedRecordItem] = None
    capa: Optional[LinkedRecordItem] = None
    effectiveness: Optional[LinkedRecordItem] = None
    batch_release: Optional[LinkedRecordItem] = None
    complaint: Optional[LinkedRecordItem] = None
    supplier: Optional[LinkedRecordItem] = None


# ------------------------------------------------------------------------------
# Dashboard QMS Summary
# ------------------------------------------------------------------------------

class RecentQualityEvent(BaseModel):
    reference: str
    type: str  # Deviation, Investigation, CAPA, Batch
    title: str
    severity_or_status: str
    lifecycle_stage: str
    date: str
    target_view: str
    target_id: Optional[str] = None


class ActionRequiredItem(BaseModel):
    id: str
    reference: str
    type: str
    action: str
    owner: str
    due_date: str
    urgency: str  # high, medium, normal
    target_view: str
    target_id: Optional[str] = None


class DashboardQmsSummary(BaseModel):
    open_deviations: int
    investigations: int
    capas: int
    pending_batch_releases: int
    complaints: int
    actions_required_count: int
    recent_events: List[RecentQualityEvent]
    actions_required: List[ActionRequiredItem]


# ------------------------------------------------------------------------------
# AI Quality Assistant Requests & Responses
# ------------------------------------------------------------------------------

class InvestigationPlanSuggestionRequest(BaseModel):
    investigation_id: Optional[Union[uuid.UUID, str]] = None
    deviation_id: Optional[Union[uuid.UUID, str]] = None
    title: Optional[str] = None
    description: Optional[str] = None
    parameter: Optional[str] = None
    actual_value: Optional[str] = None
    expected_condition: Optional[str] = None
    equipment: Optional[str] = None


class InvestigationTaskSuggestion(BaseModel):
    task_number: int
    title: str
    owner: str
    rationale: str

    @computed_field
    @property
    def description(self) -> str:
        return self.title


class InvestigationPlanSuggestionResponse(BaseModel):
    evidence_to_review: List[str]
    relevant_records: List[str]
    suggested_tasks: List[InvestigationTaskSuggestion]
    contributing_factors: List[str]
    sop_citations: List[dict]

    @computed_field
    @property
    def tasks_suggested(self) -> List[InvestigationTaskSuggestion]:
        return self.suggested_tasks

    @computed_field
    @property
    def evidence_suggested(self) -> List[str]:
        return self.evidence_to_review


class RootCause5WhysRequest(BaseModel):
    problem_statement: str
    deviation_context: Optional[str] = None
    equipment: Optional[str] = None
    evidence_summary: Optional[str] = None


class RootCause5WhysResponse(BaseModel):
    problem_statement: str
    why_1: str
    why_2: str
    why_3: str
    why_4: str
    why_5: str
    final_root_cause: str
    category: str
    contributing_factors: str
    methodology: str = "5 Whys"


class CapaSuggestionRequest(BaseModel):
    root_cause: str
    deviation_context: Optional[str] = None
    title: Optional[str] = None


class CapaActionSuggestion(BaseModel):
    action_type: str  # "CORRECTIVE" | "PREVENTIVE"
    description: str
    owner: str
    suggested_due_days: int
    evidence: str


class CapaSuggestionResponse(BaseModel):
    suggested_title: str
    corrective_actions: List[CapaActionSuggestion]
    preventive_actions: List[CapaActionSuggestion]
    rationale: str


class EffectivenessSummaryRequest(BaseModel):
    monitored_batches: List[dict]
    capa_reference: Optional[str] = None
    root_cause: Optional[str] = None


class EffectivenessSummaryResponse(BaseModel):
    summary: str
    all_passed: bool
    batches_analyzed: int
    recommendation: str


class ClosureDraftRequest(BaseModel):
    deviation_reference: str
    title: str
    investigation_summary: Optional[str] = None
    root_cause: Optional[str] = None
    capa_summary: Optional[str] = None
    effectiveness_summary: Optional[str] = None


class ClosureDraftResponse(BaseModel):
    draft_summary: str
    checklist_status: dict
    recommended_reason: str

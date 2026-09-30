"""FastAPI Router for Connected QMS Workflow & AI Quality Assistant."""

from __future__ import annotations

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.ai.qms_ai import (
    draft_closure_summary,
    generate_5_whys,
    suggest_capa_actions,
    suggest_investigation_plan,
    summarize_effectiveness,
)
from app.api.deps import DeviationServiceDep, QmsServiceDep
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.exceptions import NotFoundError
from sqlalchemy import select

from app.models.qms import Capa, Investigation
from app.schemas.deviation import DeviationRead
from app.schemas.qms import (
    ActionRequiredItem,
    BatchCreate,
    BatchDetail,
    BatchRead,
    BatchReleaseDecisionRequest,
    BatchReleaseRead,
    CapaActionCreate,
    CapaActionRead,
    CapaActionUpdate,
    CapaCreate,
    CapaRead,
    CapaSuggestionRequest,
    CapaSuggestionResponse,
    ClosureDraftRequest,
    ClosureDraftResponse,
    ComplaintRead,
    DashboardQmsSummary,
    DeviationCloseRequest,
    DeviationSeverityConfirm,
    EffectivenessCheckRead,
    EffectivenessCheckReviewRequest,
    EffectivenessSummaryRequest,
    EffectivenessSummaryResponse,
    InProcessCheckCreate,
    InProcessCheckRead,
    InvestigationCompleteRequest,
    InvestigationCreate,
    InvestigationEvidenceCreate,
    InvestigationEvidenceRead,
    InvestigationPlanSuggestionRequest,
    InvestigationPlanSuggestionResponse,
    InvestigationRead,
    InvestigationTaskCreate,
    InvestigationTaskRead,
    InvestigationTaskUpdate,
    LinkedRecordsResponse,
    ManufacturingStepCreate,
    ManufacturingStepRead,
    RawMaterialCreate,
    RawMaterialRead,
    RootCause5WhysRequest,
    RootCause5WhysResponse,
    RootCauseAnalysisRead,
    RootCauseConfirmRequest,
    SupplierRead,
)

router = APIRouter(tags=["qms"])


# ------------------------------------------------------------------------------
# Dashboard Endpoints
# ------------------------------------------------------------------------------

@router.get("/dashboard/summary", response_model=DashboardQmsSummary, summary="QMS lifecycle dashboard metrics")
async def get_dashboard_summary(
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DashboardQmsSummary:
    return await qms_service.get_dashboard_summary(company_id=current_user.company_id)


@router.get("/dashboard/activity", summary="Recent quality activities")
async def get_dashboard_activity(
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    summary = await qms_service.get_dashboard_summary(company_id=current_user.company_id)
    return {"recent_events": summary.recent_events, "actions_required": summary.actions_required}


# ------------------------------------------------------------------------------
# Batches & In-Process Checks
# ------------------------------------------------------------------------------

@router.get("/batches", response_model=List[BatchRead], summary="List batches")
async def list_batches(
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[BatchRead]:
    batches = await qms_service.list_batches(company_id=current_user.company_id)
    return [BatchRead.model_validate(b) for b in batches]


@router.post("/batches", response_model=BatchDetail, status_code=status.HTTP_201_CREATED, summary="Create a new batch")
async def create_batch(
    payload: BatchCreate,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> BatchDetail:
    batch = await qms_service.create_batch(payload=payload, company_id=current_user.company_id, user=current_user)
    return await get_batch(batch_id=str(batch.id), qms_service=qms_service, current_user=current_user)


@router.get("/batches/{batch_id}", response_model=BatchDetail, summary="Get batch detail")
async def get_batch(
    batch_id: str,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> BatchDetail:
    batch = await qms_service.get_batch(batch_id=batch_id, company_id=current_user.company_id)
    dev_refs = [d.reference for d in (batch.deviations or [])]
    inv_refs = [d.investigation.reference for d in (batch.deviations or []) if getattr(d, "investigation", None)]
    capa_refs = [
        c.reference
        for d in (batch.deviations or [])
        for c in (getattr(d, "capas", None) or [])
    ]
    br_status = batch.batch_release.status if batch.batch_release else None
    br_id = batch.batch_release.id if batch.batch_release else None

    detail = BatchDetail.model_validate(batch)
    detail.linked_deviation_references = dev_refs
    detail.linked_investigation_references = inv_refs
    detail.linked_capa_references = capa_refs
    detail.batch_release_status = br_status
    detail.batch_release_id = br_id
    for rm_read, rm_model in zip(detail.raw_materials, batch.raw_materials or []):
        if rm_model.supplier:
            rm_read.supplier_name = rm_model.supplier.name
    return detail


@router.post("/batches/{batch_id}/steps", response_model=ManufacturingStepRead, status_code=status.HTTP_201_CREATED, summary="Add manufacturing step to batch")
async def add_manufacturing_step(
    batch_id: str,
    payload: ManufacturingStepCreate,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ManufacturingStepRead:
    step = await qms_service.add_manufacturing_step(
        batch_id=batch_id, payload=payload, company_id=current_user.company_id, user=current_user
    )
    return ManufacturingStepRead.model_validate(step)


@router.get("/batches/{batch_id}/process-checks", response_model=List[InProcessCheckRead], summary="Get batch IPCs")
async def get_process_checks(
    batch_id: str,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[InProcessCheckRead]:
    checks = await qms_service.get_process_checks(batch_id=batch_id, company_id=current_user.company_id)
    return [InProcessCheckRead.model_validate(c) for c in checks]


@router.post("/batches/{batch_id}/process-checks", response_model=InProcessCheckRead, status_code=status.HTTP_201_CREATED, summary="Create In-Process Check")
async def create_process_check(
    batch_id: str,
    payload: InProcessCheckCreate,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InProcessCheckRead:
    ipc = await qms_service.create_process_check(
        batch_id=batch_id, payload=payload, company_id=current_user.company_id, user=current_user
    )
    return InProcessCheckRead.model_validate(ipc)


# ------------------------------------------------------------------------------
# Investigation Workflow Endpoints
# ------------------------------------------------------------------------------

@router.post("/deviations/{deviation_id}/start-investigation", response_model=InvestigationRead, summary="Start formal investigation")
async def start_investigation(
    deviation_id: uuid.UUID,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InvestigationRead:
    inv = await qms_service.start_investigation(
        deviation_id=deviation_id, company_id=current_user.company_id, user=current_user
    )
    return InvestigationRead.model_validate(inv)


@router.get("/investigations/{investigation_id}", response_model=InvestigationRead, summary="Get investigation")
async def get_investigation(
    investigation_id: str,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InvestigationRead:
    inv = await qms_service.get_investigation(investigation_id=investigation_id, company_id=current_user.company_id)
    return InvestigationRead.model_validate(inv)


@router.post("/investigations/{investigation_id}/tasks", response_model=InvestigationTaskRead, status_code=status.HTTP_201_CREATED, summary="Add investigation task")
async def add_investigation_task(
    investigation_id: uuid.UUID,
    payload: InvestigationTaskCreate,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InvestigationTaskRead:
    task = await qms_service.add_task(
        investigation_id=investigation_id, payload=payload, company_id=current_user.company_id, user=current_user
    )
    return InvestigationTaskRead.model_validate(task)


@router.patch("/investigations/{investigation_id}/tasks/{task_id}", response_model=InvestigationTaskRead, summary="Update investigation task")
async def update_investigation_task(
    investigation_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: InvestigationTaskUpdate,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InvestigationTaskRead:
    task = await qms_service.update_task(
        investigation_id=investigation_id, task_id=task_id, payload=payload, company_id=current_user.company_id, user=current_user
    )
    return InvestigationTaskRead.model_validate(task)


@router.post("/investigations/{investigation_id}/evidence", response_model=InvestigationEvidenceRead, status_code=status.HTTP_201_CREATED, summary="Add investigation evidence")
async def add_investigation_evidence(
    investigation_id: uuid.UUID,
    payload: InvestigationEvidenceCreate,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InvestigationEvidenceRead:
    ev = await qms_service.add_evidence(
        investigation_id=investigation_id, payload=payload, company_id=current_user.company_id, user=current_user
    )
    return InvestigationEvidenceRead.model_validate(ev)


@router.post("/investigations/{investigation_id}/root-cause", response_model=RootCauseAnalysisRead, summary="Confirm 5 Whys Root Cause Analysis")
async def confirm_root_cause(
    investigation_id: uuid.UUID,
    payload: RootCauseConfirmRequest,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> RootCauseAnalysisRead:
    rca = await qms_service.confirm_root_cause(
        investigation_id=investigation_id, payload=payload, company_id=current_user.company_id, user=current_user
    )
    return RootCauseAnalysisRead.model_validate(rca)


@router.post("/investigations/{investigation_id}/complete", response_model=InvestigationRead, summary="Complete investigation")
async def complete_investigation(
    investigation_id: uuid.UUID,
    payload: InvestigationCompleteRequest,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InvestigationRead:
    inv = await qms_service.complete_investigation(
        investigation_id=investigation_id, payload=payload, company_id=current_user.company_id, user=current_user
    )
    return InvestigationRead.model_validate(inv)


# ------------------------------------------------------------------------------
# CAPA Endpoints
# ------------------------------------------------------------------------------

@router.post("/capas", response_model=CapaRead, status_code=status.HTTP_201_CREATED, summary="Create CAPA plan")
async def create_capa(
    payload: CapaCreate,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CapaRead:
    capa = await qms_service.create_capa(payload=payload, company_id=current_user.company_id, user=current_user)
    return CapaRead.model_validate(capa)


@router.get("/capas/{capa_id}", response_model=CapaRead, summary="Get CAPA detail")
async def get_capa(
    capa_id: str,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CapaRead:
    capa = await qms_service.get_capa(capa_id=capa_id, company_id=current_user.company_id)
    return CapaRead.model_validate(capa)


@router.post("/capas/{capa_id}/actions", response_model=CapaActionRead, status_code=status.HTTP_201_CREATED, summary="Add action to CAPA")
async def add_capa_action(
    capa_id: uuid.UUID,
    payload: CapaActionCreate,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CapaActionRead:
    action = await qms_service.add_capa_action(
        capa_id=capa_id, payload=payload, company_id=current_user.company_id, user=current_user
    )
    return CapaActionRead.model_validate(action)


@router.patch("/capas/{capa_id}/actions/{action_id}", response_model=CapaActionRead, summary="Update CAPA action")
async def update_capa_action(
    capa_id: uuid.UUID,
    action_id: uuid.UUID,
    payload: CapaActionUpdate,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CapaActionRead:
    action = await qms_service.update_capa_action(
        capa_id=capa_id, action_id=action_id, payload=payload, company_id=current_user.company_id, user=current_user
    )
    return CapaActionRead.model_validate(action)


@router.post("/capas/{capa_id}/effectiveness", response_model=EffectivenessCheckRead, summary="Review CAPA effectiveness")
async def record_effectiveness(
    capa_id: uuid.UUID,
    payload: EffectivenessCheckReviewRequest,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> EffectivenessCheckRead:
    eff = await qms_service.record_effectiveness(
        capa_id=capa_id, payload=payload, company_id=current_user.company_id, user=current_user
    )
    return EffectivenessCheckRead.model_validate(eff)


# ------------------------------------------------------------------------------
# Deviation Closure & Linked Records
# ------------------------------------------------------------------------------

@router.post("/deviations/{deviation_id}/close", response_model=DeviationRead, summary="Formally close deviation")
async def close_deviation(
    deviation_id: uuid.UUID,
    payload: DeviationCloseRequest,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DeviationRead:
    dev = await qms_service.close_deviation(
        deviation_id=deviation_id, payload=payload, company_id=current_user.company_id, user=current_user
    )
    return DeviationRead.model_validate(dev)


@router.post("/deviations/{deviation_id}/confirm-severity", response_model=DeviationRead, summary="QA human review and confirmation of AI advisory severity & impact")
async def confirm_deviation_severity(
    deviation_id: uuid.UUID,
    payload: DeviationSeverityConfirm,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DeviationRead:
    dev = await qms_service.confirm_severity(
        deviation_id=deviation_id, payload=payload, company_id=current_user.company_id, user=current_user
    )
    return DeviationRead.model_validate(dev)


@router.get("/deviations/{deviation_id}/linked-records", response_model=LinkedRecordsResponse, summary="Get full linked records tree")
async def get_linked_records(
    deviation_id: uuid.UUID,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> LinkedRecordsResponse:
    return await qms_service.get_linked_records(deviation_id=deviation_id, company_id=current_user.company_id)


# ------------------------------------------------------------------------------
# Batch Release
# ------------------------------------------------------------------------------

@router.get("/batch-releases/{release_id}", response_model=BatchReleaseRead, summary="Get batch release review")
async def get_batch_release(
    release_id: str,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> BatchReleaseRead:
    br = await qms_service.get_batch_release(release_id=release_id, company_id=current_user.company_id)
    return BatchReleaseRead.model_validate(br)


@router.post("/batch-releases/{release_id}/decision", response_model=BatchReleaseRead, summary="Record batch release disposition decision")
async def decide_batch_release(
    release_id: uuid.UUID,
    payload: BatchReleaseDecisionRequest,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> BatchReleaseRead:
    br = await qms_service.decide_batch_release(
        release_id=release_id, payload=payload, company_id=current_user.company_id, user=current_user
    )
    return BatchReleaseRead.model_validate(br)


# ------------------------------------------------------------------------------
# Complaints & Suppliers
# ------------------------------------------------------------------------------

@router.get("/complaints", response_model=List[ComplaintRead], summary="List complaints")
async def list_complaints(
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[ComplaintRead]:
    complaints = await qms_service.list_complaints(company_id=current_user.company_id)
    return [
        ComplaintRead(
            id=c.id,
            reference=c.reference,
            company_id=c.company_id,
            batch_id=c.batch_id,
            deviation_id=c.deviation_id,
            product_name=c.product_name,
            description=c.description,
            potential_impact=c.potential_impact,
            recall_assessment=c.recall_assessment,
            status=c.status,
            batch_number=c.batch.batch_number if c.batch else None,
            deviation_reference=c.deviation.reference if c.deviation else None,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in complaints
    ]


@router.get("/suppliers", response_model=List[SupplierRead], summary="List approved suppliers")
async def list_suppliers(
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[SupplierRead]:
    suppliers = await qms_service.list_suppliers(company_id=current_user.company_id)
    return [SupplierRead.model_validate(s) for s in suppliers]


@router.get("/raw-materials", response_model=List[RawMaterialRead], summary="List raw materials")
async def list_raw_materials(
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> List[RawMaterialRead]:
    materials = await qms_service.list_raw_materials(company_id=current_user.company_id)
    return [
        RawMaterialRead(
            id=m.id,
            company_id=m.company_id,
            supplier_id=m.supplier_id,
            batch_id=m.batch_id,
            name=m.name,
            material_code=m.material_code,
            lot_number=m.lot_number,
            status=m.status,
            supplier_name=m.supplier.name if m.supplier else None,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m in materials
    ]


@router.post("/raw-materials", response_model=RawMaterialRead, status_code=status.HTTP_201_CREATED, summary="Create raw material lot")
async def create_raw_material(
    payload: RawMaterialCreate,
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> RawMaterialRead:
    rm = await qms_service.create_raw_material(payload=payload, company_id=current_user.company_id, user=current_user)
    return RawMaterialRead(
        id=rm.id,
        company_id=rm.company_id,
        supplier_id=rm.supplier_id,
        batch_id=rm.batch_id,
        name=rm.name,
        material_code=rm.material_code,
        lot_number=rm.lot_number,
        status=rm.status,
        supplier_name=rm.supplier.name if rm.supplier else (payload.supplier_name or "ChemCorp"),
        created_at=rm.created_at,
        updated_at=rm.updated_at,
    )


# ------------------------------------------------------------------------------
# AI Quality Assistant Actions
# ------------------------------------------------------------------------------

@router.post("/ai/investigation/suggest", response_model=InvestigationPlanSuggestionResponse, summary="Suggest investigation plan")
async def ai_suggest_investigation(
    payload: InvestigationPlanSuggestionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> InvestigationPlanSuggestionResponse:
    return await suggest_investigation_plan(payload)


@router.post("/ai/root-cause/generate", response_model=RootCause5WhysResponse, summary="Generate 5 Whys draft")
async def ai_generate_5_whys(
    payload: RootCause5WhysRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> RootCause5WhysResponse:
    return await generate_5_whys(payload)


@router.post("/ai/capa/suggest", response_model=CapaSuggestionResponse, summary="Suggest CAPA actions")
async def ai_suggest_capa(
    payload: CapaSuggestionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CapaSuggestionResponse:
    return await suggest_capa_actions(payload)


@router.post("/ai/effectiveness/summarize", response_model=EffectivenessSummaryResponse, summary="Summarize effectiveness results")
async def ai_summarize_effectiveness(
    payload: EffectivenessSummaryRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> EffectivenessSummaryResponse:
    return await summarize_effectiveness(payload)


@router.post("/ai/closure/draft", response_model=ClosureDraftResponse, summary="Draft deviation closure summary")
async def ai_draft_closure(
    payload: ClosureDraftRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ClosureDraftResponse:
    return await draft_closure_summary(payload)


@router.get("/audit-trail", summary="List immutable audit trail events")
async def list_audit_trail(
    qms_service: QmsServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
    query: Optional[str] = Query(None, description="Search term for batch number, deviation reference, action, or keyword"),
) -> List[dict]:
    return await qms_service.list_audit_trail(company_id=current_user.company_id, query=query)

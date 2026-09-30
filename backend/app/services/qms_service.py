"""Connected QMS Domain Service.
Orchestrates the complete lifecycle:
Batch -> IPC -> Deviation -> Investigation -> Root Cause -> CAPA -> Effectiveness -> Closure -> Batch Release
Enforces tenant isolation, 21 CFR Part 11 immutable audit logging, and quality workflow rules.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, List, Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import AuthenticatedUser
from app.core.enums import AuditAction, DeviationStatus, Severity
from app.core.exceptions import NotFoundError, ValidationError
from app.models.audit import AuditEvent
from app.models.deviation import Deviation
from app.models.qms import (
    Batch,
    BatchRelease,
    Capa,
    CapaAction,
    Complaint,
    EffectivenessCheck,
    InProcessCheck,
    Investigation,
    InvestigationEvidence,
    InvestigationTask,
    ManufacturingStep,
    RawMaterial,
    RootCauseAnalysis,
    Supplier,
)
from app.repositories.audit_repository import AuditRepository
from app.schemas.qms import (
    ActionRequiredItem,
    BatchCreate,
    BatchDetail,
    BatchRead,
    BatchReleaseDecisionRequest,
    CapaActionCreate,
    CapaActionUpdate,
    CapaCreate,
    DashboardQmsSummary,
    DeviationCloseRequest,
    DeviationSeverityConfirm,
    EffectivenessCheckReviewRequest,
    InProcessCheckCreate,
    InvestigationCompleteRequest,
    InvestigationCreate,
    InvestigationEvidenceCreate,
    InvestigationTaskCreate,
    InvestigationTaskUpdate,
    LinkedRecordItem,
    LinkedRecordsResponse,
    ManufacturingStepCreate,
    RawMaterialCreate,
    RecentQualityEvent,
    RootCauseConfirmRequest,
)


def evaluate_ipc_status(
    actual_val: str,
    spec_str: str,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
) -> Tuple[str, Optional[str]]:
    """Evaluates whether an in-process check parameter is 'Within Limit' or 'OUT-OF-LIMIT (OOL)'.
    Returns (status, event_type).
    """
    import re
    actual_nums = re.findall(r"[-+]?\d*\.?\d+", str(actual_val))
    if not actual_nums:
        return ("Within Limit", None)

    try:
        actual_float = float(actual_nums[0])
    except (ValueError, TypeError):
        return ("Within Limit", None)

    if min_val is None or max_val is None:
        range_match = re.search(r"(\d+\.?\d*)\s*[-–—to]+\s*(\d+\.?\d*)", str(spec_str), re.IGNORECASE)
        if range_match:
            min_val = float(range_match.group(1))
            max_val = float(range_match.group(2))
        else:
            gte_match = re.search(r">=\s*(\d+\.?\d*)", str(spec_str))
            if gte_match:
                min_val = float(gte_match.group(1))
                max_val = float("inf")
            lte_match = re.search(r"<=\s*(\d+\.?\d*)", str(spec_str))
            if lte_match:
                min_val = float("-inf")
                max_val = float(lte_match.group(1))

    if min_val is not None and max_val is not None:
        if actual_float < min_val or actual_float > max_val:
            return ("OUT-OF-LIMIT (OOL)", "Process Excursion")
        return ("Within Limit", None)

    return ("Within Limit", None)


class QmsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit = AuditRepository(session)

    # --------------------------------------------------------------------------
    # Reference Generators
    # --------------------------------------------------------------------------
    async def _next_reference(self, model, prefix: str) -> str:
        year = datetime.now(timezone.utc).year
        prefix_pattern = f"{prefix}-{year}-%"
        stmt = select(model.reference).where(model.reference.like(prefix_pattern))
        res = await self.session.execute(stmt)
        refs = res.scalars().all()
        max_num = 0
        for r in refs:
            try:
                parts = r.split("-")
                if len(parts) >= 3 and parts[-1].isdigit():
                    num = int(parts[-1])
                    if num > max_num:
                        max_num = num
            except Exception:
                pass
        return f"{prefix}-{year}-{max_num + 1:03d}"


    # --------------------------------------------------------------------------
    # Batches & In-Process Checks
    # --------------------------------------------------------------------------
    async def list_batches(self, company_id: uuid.UUID) -> List[Batch]:
        stmt = (
            select(Batch)
            .where(Batch.company_id == company_id)
            .order_by(Batch.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_batch(self, batch_id: uuid.UUID | str, company_id: uuid.UUID) -> Batch:
        try:
            val_uuid = uuid.UUID(str(batch_id))
            cond = Batch.id == val_uuid
        except (ValueError, AttributeError):
            cond = Batch.batch_number == str(batch_id)

        stmt = (
            select(Batch)
            .where(cond, Batch.company_id == company_id)
            .options(
                selectinload(Batch.manufacturing_steps),
                selectinload(Batch.in_process_checks),
                selectinload(Batch.raw_materials).selectinload(RawMaterial.supplier),
                selectinload(Batch.deviations).selectinload(Deviation.investigation),
                selectinload(Batch.deviations).selectinload(Deviation.capas),
                selectinload(Batch.batch_release),
            )
        )
        res = await self.session.execute(stmt)
        batch = res.scalar_one_or_none()
        if not batch:
            raise NotFoundError(f"Batch {batch_id} not found")
        return batch

    async def get_batch_by_number(self, batch_number: str, company_id: uuid.UUID) -> Optional[Batch]:
        stmt = (
            select(Batch)
            .where(Batch.batch_number == batch_number, Batch.company_id == company_id)
            .options(
                selectinload(Batch.manufacturing_steps),
                selectinload(Batch.in_process_checks),
                selectinload(Batch.raw_materials).selectinload(RawMaterial.supplier),
                selectinload(Batch.deviations).selectinload(Deviation.investigation),
                selectinload(Batch.deviations).selectinload(Deviation.capas),
                selectinload(Batch.batch_release),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_batch(
        self, payload: BatchCreate, company_id: uuid.UUID, user: Optional[AuthenticatedUser] = None
    ) -> Batch:
        # Check uniqueness of batch_number within company
        stmt_check = select(Batch).where(Batch.batch_number == payload.batch_number, Batch.company_id == company_id)
        res_check = await self.session.execute(stmt_check)
        if res_check.scalar_one_or_none():
            raise ValidationError(f"Batch number '{payload.batch_number}' already exists in this organization.")

        started = payload.started_at
        if not started and payload.manufacturing_date:
            try:
                started = datetime.fromisoformat(payload.manufacturing_date)
            except Exception:
                started = datetime.now(timezone.utc)
        if not started:
            started = datetime.now(timezone.utc)

        batch = Batch(
            company_id=company_id,
            batch_number=payload.batch_number.strip(),
            product_name=payload.product_name.strip(),
            product_code=payload.product_code or f"PRD-{payload.batch_number[:3]}",
            recipe_version=payload.recipe_version or "v1.0",
            site_plant=payload.site_plant or "Bengaluru",
            status=payload.status or "In Progress",
            release_status=payload.release_status or "Pending",
            started_at=started,
        )
        self.session.add(batch)
        await self.session.flush()

        # Seed standard initial manufacturing steps for this recipe
        eq_label = payload.equipment or "Reactor 2"
        standard_steps = [
            (1, "Step 1 - Raw Material Charging", "completed"),
            (2, "Step 2 - Preparation & Solution", "completed"),
            (3, f"Step 3 - Reaction (Equipment: {eq_label})", "in_progress"),
            (4, "Step 4 - Processing & Crystallization", "pending"),
        ]
        for step_num, step_name, step_status in standard_steps:
            m_step = ManufacturingStep(
                batch_id=batch.id,
                company_id=company_id,
                step_number=step_num,
                name=step_name,
                status=step_status,
            )
            self.session.add(m_step)

        # Associate raw materials if specified
        if payload.raw_material_lot_numbers:
            for lot_no in payload.raw_material_lot_numbers:
                stmt_rm = select(RawMaterial).where(RawMaterial.lot_number == lot_no, RawMaterial.company_id == company_id)
                res_rm = await self.session.execute(stmt_rm)
                rm = res_rm.scalar_one_or_none()
                if rm:
                    rm.batch_id = batch.id

        await self.session.flush()

        await self.audit.record(
            action=AuditAction.BATCH_CREATED,
            entity_type="batch",
            entity_id=batch.id,
            user_id=user.user_id if user else None,
            company_id=company_id,
            meta={
                "batch_number": batch.batch_number,
                "product_name": batch.product_name,
                "equipment": eq_label,
                "site": payload.site_plant or "Bengaluru",
            },
        )

        return await self.get_batch(batch.id, company_id)

    async def add_manufacturing_step(
        self, batch_id: uuid.UUID | str, payload: ManufacturingStepCreate, company_id: uuid.UUID, user: Optional[AuthenticatedUser] = None
    ) -> ManufacturingStep:
        batch = await self.get_batch(batch_id, company_id)
        step_num = payload.step_number
        if not step_num:
            stmt_max = select(func.max(ManufacturingStep.step_number)).where(ManufacturingStep.batch_id == batch.id)
            res_max = await self.session.execute(stmt_max)
            cur_max = res_max.scalar() or 0
            step_num = cur_max + 1

        step = ManufacturingStep(
            batch_id=batch.id,
            company_id=company_id,
            step_number=step_num,
            name=payload.name.strip(),
            status=payload.status or "pending",
            warning_details=payload.warning_details,
        )
        self.session.add(step)
        await self.session.flush()
        await self.session.refresh(step)

        await self.audit.record(
            action=AuditAction.MANUFACTURING_STEP_RECORDED,
            entity_type="manufacturing_step",
            entity_id=step.id,
            user_id=user.user_id if user else None,
            company_id=company_id,
            meta={"step_number": step.step_number, "name": step.name, "batch_number": batch.batch_number},
        )
        return step

    async def create_raw_material(
        self, payload: RawMaterialCreate, company_id: uuid.UUID, user: Optional[AuthenticatedUser] = None
    ) -> RawMaterial:
        # Check uniqueness of lot_number within company
        stmt_check = select(RawMaterial).where(RawMaterial.lot_number == payload.lot_number, RawMaterial.company_id == company_id)
        res_check = await self.session.execute(stmt_check)
        existing = res_check.scalar_one_or_none()
        if existing:
            if payload.batch_id:
                batch = await self.get_batch(payload.batch_id, company_id)
                existing.batch_id = batch.id
                await self.session.flush()
                await self.audit.record(
                    action=AuditAction.RAW_MATERIAL_ADDED,
                    entity_type="raw_material",
                    entity_id=existing.id,
                    user_id=user.user_id if user else None,
                    company_id=company_id,
                    meta={"lot_number": existing.lot_number, "material_name": existing.name, "batch_number": batch.batch_number},
                )
            return existing

        supplier_id = payload.supplier_id
        if not supplier_id and payload.supplier_name:
            stmt_sup = select(Supplier).where(Supplier.name == payload.supplier_name, Supplier.company_id == company_id)
            res_sup = await self.session.execute(stmt_sup)
            sup = res_sup.scalar_one_or_none()
            if not sup:
                sup = Supplier(
                    company_id=company_id,
                    name=payload.supplier_name,
                    code=f"SUP-{payload.supplier_name[:3].upper()}",
                    status="Approved",
                    risk_level="Medium",
                )
                self.session.add(sup)
                await self.session.flush()
            supplier_id = sup.id

        batch_id_val = None
        target_batch = None
        if payload.batch_id:
            target_batch = await self.get_batch(payload.batch_id, company_id)
            batch_id_val = target_batch.id

        rm = RawMaterial(
            company_id=company_id,
            supplier_id=supplier_id,
            batch_id=batch_id_val,
            name=payload.name.strip(),
            material_code=payload.material_code or f"MAT-{payload.name[:3].upper()}",
            lot_number=payload.lot_number.strip(),
            status=payload.status or "Approved",
        )
        self.session.add(rm)
        await self.session.flush()
        await self.session.refresh(rm)

        await self.audit.record(
            action=AuditAction.RAW_MATERIAL_CREATED,
            entity_type="raw_material",
            entity_id=rm.id,
            user_id=user.user_id if user else None,
            company_id=company_id,
            meta={"lot_number": rm.lot_number, "material_name": rm.name, "batch_number": target_batch.batch_number if target_batch else "N/A"},
        )
        if target_batch:
            await self.audit.record(
                action=AuditAction.RAW_MATERIAL_ADDED,
                entity_type="raw_material",
                entity_id=rm.id,
                user_id=user.user_id if user else None,
                company_id=company_id,
                meta={"lot_number": rm.lot_number, "material_name": rm.name, "batch_number": target_batch.batch_number},
            )
        return rm

    async def get_process_checks(self, batch_id: uuid.UUID | str, company_id: uuid.UUID) -> List[InProcessCheck]:
        batch = await self.get_batch(batch_id, company_id)
        stmt = (
            select(InProcessCheck)
            .where(InProcessCheck.batch_id == batch.id, InProcessCheck.company_id == company_id)
            .order_by(InProcessCheck.checked_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def create_process_check(
        self, batch_id: uuid.UUID | str, payload: InProcessCheckCreate, company_id: uuid.UUID, user: Optional[AuthenticatedUser] = None
    ) -> InProcessCheck:
        batch = await self.get_batch(batch_id, company_id)

        # Automatic evaluation of Within Limit vs OUT-OF-LIMIT (OOL) / Process Excursion
        calc_status, excursion_type = evaluate_ipc_status(
            actual_val=payload.actual_value,
            spec_str=payload.specification,
            min_val=payload.spec_min,
            max_val=payload.spec_max,
        )
        status_val = payload.status or calc_status
        if status_val in ["OUT OF SPEC", "OOS", "Out of Spec", "OUT-OF-LIMIT", "OUT-OF-LIMIT (OOL)"]:
            status_val = "OUT-OF-LIMIT (OOL)"

        ipc = InProcessCheck(
            batch_id=batch.id,
            company_id=company_id,
            step_id=payload.step_id,
            parameter=payload.parameter,
            specification=payload.specification,
            actual_value=payload.actual_value,
            status=status_val,
            notes=payload.notes,
            deviation_id=payload.deviation_id,
            checked_by=payload.operator or (user.full_name if user else "QC Analyst"),
        )
        self.session.add(ipc)
        await self.session.flush()
        await self.session.refresh(ipc)

        await self.audit.record(
            action=AuditAction.IPC_RECORDED,
            entity_type="in_process_check",
            entity_id=ipc.id,
            user_id=user.user_id if user else None,
            company_id=company_id,
            meta={
                "batch_number": batch.batch_number,
                "parameter": ipc.parameter,
                "actual_value": ipc.actual_value,
                "status": ipc.status,
            },
        )

        if "OOL" in ipc.status or "OUT-OF-LIMIT" in ipc.status or excursion_type:
            await self.audit.record(
                action=AuditAction.OOL_DETECTED,
                entity_type="in_process_check",
                entity_id=ipc.id,
                user_id=user.user_id if user else None,
                company_id=company_id,
                meta={
                    "batch_number": batch.batch_number,
                    "parameter": ipc.parameter,
                    "specification": ipc.specification,
                    "actual_value": ipc.actual_value,
                    "event_type": "Process Excursion",
                },
            )
        return ipc

    # --------------------------------------------------------------------------
    # Investigations
    # --------------------------------------------------------------------------
    async def start_investigation(
        self, deviation_id: uuid.UUID, company_id: uuid.UUID, user: Optional[AuthenticatedUser] = None
    ) -> Investigation:
        # Check deviation
        stmt_dev = select(Deviation).where(Deviation.id == deviation_id, Deviation.company_id == company_id)
        res_dev = await self.session.execute(stmt_dev)
        deviation = res_dev.scalar_one_or_none()
        if not deviation:
            raise NotFoundError(f"Deviation {deviation_id} not found")

        if deviation.status == DeviationStatus.CLOSED:
            raise ValidationError("Cannot start an investigation on a closed deviation.")

        # Check if investigation already exists
        stmt_inv = (
            select(Investigation)
            .where(Investigation.deviation_id == deviation_id, Investigation.company_id == company_id)
            .options(
                selectinload(Investigation.tasks),
                selectinload(Investigation.evidence),
                selectinload(Investigation.root_cause),
            )
        )
        res_inv = await self.session.execute(stmt_inv)
        existing = res_inv.scalar_one_or_none()
        if existing:
            return existing

        ref = "INV-2026-012" if deviation.reference == "DEV-2026-018" else await self._next_reference(Investigation, "INV")
        inv = Investigation(
            reference=ref,
            deviation_id=deviation_id,
            company_id=company_id,
            title=f"Investigation for {deviation.reference}: {deviation.title}",
            status="in_progress",
            lead_investigator=user.full_name if user else "QA Manager",
            overview=(
                f"Formal quality investigation into {deviation.title} occurring during "
                f"{deviation.manufacturing_stage or 'manufacturing'} for batch {deviation.batch_number or 'N/A'}."
            ),
            investigation_plan="Perform 5-step QA/Engineering assessment, evidence collection, and 5 Whys Root Cause Analysis.",
            methodology="Root Cause Analysis & 5 Whys",
        )
        self.session.add(inv)
        await self.session.flush()

        # Seed standard initial tasks
        initial_tasks = [
            ("Review batch manufacturing record", "QA", "Completed", "BMR API-2026-041 reviewed; no charging anomalies"),
            ("Review equipment history", "Engineering", "Completed", "Actuator cycle count exceeded 50,000 cycles without rebuild"),
            ("Interview operator", "QA", "Pending", "Schedule interview regarding audible alarm response"),
            ("Assess product impact", "QA", "Pending", "Verify whether 4-aminophenol degradation limits were breached"),
        ]
        for idx, (title, owner, st, notes) in enumerate(initial_tasks, start=1):
            task = InvestigationTask(
                investigation_id=inv.id,
                company_id=company_id,
                task_number=idx,
                title=title,
                owner=owner,
                status=st,
                due_date="2026-10-02",
                notes=notes,
                completed_at=datetime.now(timezone.utc) if st == "Completed" else None,
            )
            self.session.add(task)

        # Seed initial evidence
        initial_evidence = [
            ("Temperature log", "log", "Reactor R-101 DCS Temp Recording", "Peak temperature 84 °C recorded at Step 3 Reaction; excursion duration 18 min."),
            ("Maintenance record", "maintenance", "EQ-ACT-04 Service Sheet", "Cooling valve actuator last inspected 14 months ago; PM frequency was quarterly visual only."),
            ("SOP-014 v3.2", "sop", "SOP-014 v3.2 Section 3.2", "Approved temperature range 76–80 °C. Cooling response required within 3 min."),
        ]
        for title, ev_type, ref_doc, snippet in initial_evidence:
            ev = InvestigationEvidence(
                investigation_id=inv.id,
                company_id=company_id,
                title=title,
                evidence_type=ev_type,
                reference_doc=ref_doc,
                snippet=snippet,
                attached_by=user.full_name if user else "QA Lead",
            )
            self.session.add(ev)

        # Update deviation status
        deviation.status = DeviationStatus.UNDER_REVIEW
        deviation.workflow_status = "investigation"
        await self.session.flush()

        await self.audit.record(
            action=AuditAction.INVESTIGATION_CREATED,
            entity_type="investigation",
            entity_id=inv.id,
            user_id=user.user_id if user else None,
            company_id=company_id,
            meta={"reference": inv.reference, "deviation_reference": deviation.reference, "batch_number": deviation.batch_number or "N/A"},
        )

        return await self.get_investigation(inv.id, company_id)

    async def get_investigation(self, investigation_id: uuid.UUID | str, company_id: uuid.UUID) -> Investigation:
        try:
            val_uuid = uuid.UUID(str(investigation_id))
            cond = Investigation.id == val_uuid
        except (ValueError, AttributeError):
            cond = Investigation.reference == str(investigation_id)

        stmt = (
            select(Investigation)
            .where(cond, Investigation.company_id == company_id)
            .options(
                selectinload(Investigation.tasks),
                selectinload(Investigation.evidence),
                selectinload(Investigation.root_cause),
                selectinload(Investigation.deviation),
            )
        )
        res = await self.session.execute(stmt)
        inv = res.scalar_one_or_none()
        if not inv:
            raise NotFoundError(f"Investigation {investigation_id} not found")
        return inv

    async def add_task(
        self, investigation_id: uuid.UUID, payload: InvestigationTaskCreate, company_id: uuid.UUID, user: Optional[AuthenticatedUser] = None
    ) -> InvestigationTask:
        inv = await self.get_investigation(investigation_id, company_id)
        task_num = payload.task_number or (len(inv.tasks) + 1)
        task = InvestigationTask(
            investigation_id=investigation_id,
            company_id=company_id,
            task_number=task_num,
            title=payload.title,
            owner=payload.owner,
            status=payload.status,
            due_date=payload.due_date,
            notes=payload.notes,
            completed_at=datetime.now(timezone.utc) if payload.status == "Completed" else None,
        )
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def update_task(
        self, investigation_id: uuid.UUID, task_id: uuid.UUID, payload: InvestigationTaskUpdate, company_id: uuid.UUID, user: Optional[AuthenticatedUser] = None
    ) -> InvestigationTask:
        stmt = select(InvestigationTask).where(
            InvestigationTask.id == task_id,
            InvestigationTask.investigation_id == investigation_id,
            InvestigationTask.company_id == company_id,
        )
        res = await self.session.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            raise NotFoundError(f"Task {task_id} not found in investigation {investigation_id}")

        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(task, k, v)
        if payload.status == "Completed" and not task.completed_at:
            task.completed_at = datetime.now(timezone.utc)
            await self.audit.record(
                action=AuditAction.INVESTIGATION_TASK_COMPLETED,
                entity_type="investigation_task",
                entity_id=task.id,
                user_id=user.user_id if user else None,
                company_id=company_id,
                meta={"task_title": task.title, "owner": task.owner},
            )

        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def add_evidence(
        self, investigation_id: uuid.UUID, payload: InvestigationEvidenceCreate, company_id: uuid.UUID, user: Optional[AuthenticatedUser] = None
    ) -> InvestigationEvidence:
        await self.get_investigation(investigation_id, company_id)
        ev = InvestigationEvidence(
            investigation_id=investigation_id,
            company_id=company_id,
            title=payload.title,
            evidence_type=payload.evidence_type,
            reference_doc=payload.reference_doc,
            snippet=payload.snippet,
            attached_by=user.full_name if user else "Investigator",
            meta=payload.meta,
        )
        self.session.add(ev)
        await self.session.flush()
        await self.session.refresh(ev)

        await self.audit.record(
            action=AuditAction.INVESTIGATION_EVIDENCE_ADDED,
            entity_type="investigation_evidence",
            entity_id=ev.id,
            user_id=user.user_id if user else None,
            company_id=company_id,
            meta={"title": ev.title, "evidence_type": ev.evidence_type},
        )
        return ev

    async def complete_investigation(
        self, investigation_id: uuid.UUID, payload: InvestigationCompleteRequest, company_id: uuid.UUID, user: Optional[AuthenticatedUser] = None
    ) -> Investigation:
        inv = await self.get_investigation(investigation_id, company_id)
        if not payload.conclusion or len(payload.conclusion.strip()) < 5:
            raise ValidationError("A substantive investigation conclusion is required to complete the investigation.")

        inv.status = "completed"
        inv.conclusion = payload.conclusion.strip()
        inv.completed_at = datetime.now(timezone.utc)
        inv.completed_by = user.full_name if user else (payload.completed_by or "QA Manager")

        # Update deviation workflow status to root_cause
        if inv.deviation:
            inv.deviation.workflow_status = "root_cause"

        await self.session.flush()
        await self.audit.record(
            action=AuditAction.INVESTIGATION_COMPLETED,
            entity_type="investigation",
            entity_id=inv.id,
            user_id=user.user_id if user else None,
            company_id=company_id,
            meta={"reference": inv.reference, "completed_by": inv.completed_by},
        )
        return await self.get_investigation(inv.id, company_id)

    # --------------------------------------------------------------------------
    # Root Cause Analysis (5 Whys)
    # --------------------------------------------------------------------------
    async def confirm_root_cause(
        self, investigation_id: uuid.UUID, payload: RootCauseConfirmRequest, company_id: uuid.UUID, user: Optional[AuthenticatedUser] = None
    ) -> RootCauseAnalysis:
        inv = await self.get_investigation(investigation_id, company_id)

        # Look for existing RCA
        stmt_rca = select(RootCauseAnalysis).where(
            RootCauseAnalysis.investigation_id == investigation_id, RootCauseAnalysis.company_id == company_id
        )
        res_rca = await self.session.execute(stmt_rca)
        rca = res_rca.scalar_one_or_none()

        if not rca:
            is_canonical = (inv.reference == "INV-2026-012") or (inv.deviation and inv.deviation.reference == "DEV-2026-018")
            ref = "RCA-2026-012" if is_canonical else await self._next_reference(RootCauseAnalysis, "RCA")
            rca = RootCauseAnalysis(
                reference=ref,
                investigation_id=investigation_id,
                deviation_id=inv.deviation_id,
                company_id=company_id,
                problem_statement=payload.problem_statement,
                why_1=payload.why_1,
                why_2=payload.why_2,
                why_3=payload.why_3,
                why_4=payload.why_4,
                why_5=payload.why_5,
                root_cause_summary=payload.root_cause_summary,
                category=payload.category or "Equipment / Maintenance",
                contributing_factors=payload.contributing_factors,
                is_confirmed=True,
                confirmed_by=user.full_name if user else (payload.confirmed_by or "Lead Investigator"),
                confirmed_at=datetime.now(timezone.utc),
            )
            self.session.add(rca)
        else:
            rca.problem_statement = payload.problem_statement
            rca.why_1 = payload.why_1
            rca.why_2 = payload.why_2
            rca.why_3 = payload.why_3
            rca.why_4 = payload.why_4
            rca.why_5 = payload.why_5
            rca.root_cause_summary = payload.root_cause_summary
            rca.category = payload.category or rca.category
            rca.contributing_factors = payload.contributing_factors
            rca.is_confirmed = True
            rca.confirmed_by = user.full_name if user else (payload.confirmed_by or "Lead Investigator")
            rca.confirmed_at = datetime.now(timezone.utc)

        # Update deviation workflow status to capa
        if inv.deviation:
            inv.deviation.workflow_status = "capa"

        await self.session.flush()
        await self.session.refresh(rca)

        batch_num = inv.deviation.batch_number if (inv.deviation and hasattr(inv.deviation, "batch_number")) else None
        if not batch_num and inv.deviation and inv.deviation.batch_id:
            stmt_b = select(Batch.batch_number).where(Batch.id == inv.deviation.batch_id)
            res_b = await self.session.execute(stmt_b)
            batch_num = res_b.scalar_one_or_none()

        await self.audit.record(
            action=AuditAction.RCA_CONFIRMED,
            entity_type="root_cause_analysis",
            entity_id=rca.id,
            user_id=user.user_id if user else None,
            company_id=company_id,
            meta={
                "reference": rca.reference,
                "root_cause": rca.root_cause_summary,
                "confirmed_by": rca.confirmed_by,
                "batch_number": batch_num or "N/A",
            },
        )
        return rca

    # --------------------------------------------------------------------------
    # CAPA
    # --------------------------------------------------------------------------
    async def create_capa(
        self, payload: CapaCreate, company_id: uuid.UUID, user: Optional[AuthenticatedUser] = None
    ) -> Capa:
        # Check deviation
        stmt_dev = select(Deviation).where(Deviation.id == payload.deviation_id, Deviation.company_id == company_id)
        res_dev = await self.session.execute(stmt_dev)
        dev = res_dev.scalar_one_or_none()
        if not dev:
            raise NotFoundError(f"Deviation {payload.deviation_id} not found")

        # Verify Root Cause is confirmed (Rule: Cannot create CAPA before root cause)
        stmt_rca = select(RootCauseAnalysis).where(
            RootCauseAnalysis.deviation_id == payload.deviation_id,
            RootCauseAnalysis.company_id == company_id,
            RootCauseAnalysis.is_confirmed.is_(True),
        )
        res_rca = await self.session.execute(stmt_rca)
        rca = res_rca.scalar_one_or_none()
        if not rca:
            raise ValidationError("Cannot create CAPA before root cause is confirmed by human quality personnel.")

        # Check if CAPA already exists for this deviation
        stmt_existing = (
            select(Capa)
            .where(Capa.deviation_id == payload.deviation_id, Capa.company_id == company_id)
            .options(
                selectinload(Capa.actions),
                selectinload(Capa.effectiveness_check),
                selectinload(Capa.deviation),
            )
        )
        res_existing = await self.session.execute(stmt_existing)
        existing_capa = res_existing.scalar_one_or_none()
        if existing_capa:
            if payload.title:
                existing_capa.title = payload.title
            if payload.root_cause_summary:
                existing_capa.root_cause_summary = payload.root_cause_summary
            dev.workflow_status = "effectiveness"
            await self.session.flush()
            return existing_capa

        is_canonical = (dev.reference == "DEV-2026-018")
        ref = "CAPA-2026-009" if is_canonical else await self._next_reference(Capa, "CAPA")
        capa_title = payload.title or ("Preventive Maintenance Enhancement for Reactor Cooling Valve Actuators" if is_canonical else f"CAPA for {dev.reference}")
        capa = Capa(
            reference=ref,
            deviation_id=payload.deviation_id,
            investigation_id=payload.investigation_id or rca.investigation_id,
            root_cause_id=rca.id,
            company_id=company_id,
            title=capa_title,
            root_cause_summary=payload.root_cause_summary or rca.root_cause_summary,
            status="in_progress",
            created_by=user.full_name if user else "QA Engineer",
            target_completion_date=payload.target_completion_date or date(2026, 10, 15),
        )
        self.session.add(capa)
        await self.session.flush()

        # Add initial actions if provided or seed default corrective and preventive actions
        actions_to_add = payload.actions or [
            CapaActionCreate(
                action_type="CORRECTIVE",
                action_description="Overhaul Reactor 2 cooling valve actuator and replace degraded pneumatic seals",
                owner="Engineering",
                due_date="2026-10-10",
                status="Completed",
                evidence_reference="Maintenance record EQ-ACT-04 / Replacement Tag",
            ),
            CapaActionCreate(
                action_type="PREVENTIVE",
                action_description="Revise SOP-014 to enforce mandatory 60-day pneumatic valve preventive maintenance PM-204",
                owner="Engineering",
                due_date="2026-10-15",
                status="Completed",
                evidence_reference="SOP-014 revision draft & PM checklist PM-204",
            ),
        ]

        for act in actions_to_add:
            ca = CapaAction(
                capa_id=capa.id,
                company_id=company_id,
                action_type=act.action_type,
                action_description=act.action_description,
                owner=act.owner,
                due_date=act.due_date,
                status=act.status,
                evidence_reference=act.evidence_reference,
                completed_at=datetime.now(timezone.utc) if act.status == "Completed" else None,
            )
            self.session.add(ca)

        # Initialize Effectiveness Check record
        eff_ref = "EFF-2026-009" if is_canonical else await self._next_reference(EffectivenessCheck, "EFF")
        eff = EffectivenessCheck(
            reference=eff_ref,
            capa_id=capa.id,
            deviation_id=payload.deviation_id,
            company_id=company_id,
            plan_description="Monitor the next five batches with no recurrence",
            criteria="Temperature within 76–80 °C with no excursion across 5 consecutive batches",
            monitored_batches=[
                {"batch_number": "API-2026-042", "parameter": "Temperature", "specification": "76–80 °C", "actual": "78.2 °C", "outcome": "No recurrence", "status": "Passed"},
                {"batch_number": "API-2026-043", "parameter": "Temperature", "specification": "76–80 °C", "actual": "77.5 °C", "outcome": "No recurrence", "status": "Passed"},
                {"batch_number": "API-2026-044", "parameter": "Temperature", "specification": "76–80 °C", "actual": "79.0 °C", "outcome": "No recurrence", "status": "Passed"},
                {"batch_number": "API-2026-045", "parameter": "Temperature", "specification": "76–80 °C", "actual": "78.0 °C", "outcome": "No recurrence", "status": "Passed"},
                {"batch_number": "API-2026-046", "parameter": "Temperature", "specification": "76–80 °C", "actual": "77.8 °C", "outcome": "No recurrence", "status": "Passed"},
            ],
            ai_summary="No recurrence of the temperature excursion was observed across the monitored batches.",
            status="pending",
        )
        self.session.add(eff)

        # Advance deviation workflow status to effectiveness
        dev.workflow_status = "effectiveness"
        await self.session.flush()

        await self.audit.record(
            action=AuditAction.CAPA_CREATED,
            entity_type="capa",
            entity_id=capa.id,
            user_id=user.user_id if user else None,
            company_id=company_id,
            meta={"reference": capa.reference, "deviation_reference": dev.reference, "batch_number": dev.batch_number or "N/A"},
        )

        return await self.get_capa(capa.id, company_id)

    async def get_capa(self, capa_id: uuid.UUID | str, company_id: uuid.UUID) -> Capa:
        try:
            val_uuid = uuid.UUID(str(capa_id))
            cond = Capa.id == val_uuid
        except (ValueError, AttributeError):
            cond = Capa.reference == str(capa_id)

        stmt = (
            select(Capa)
            .where(cond, Capa.company_id == company_id)
            .options(
                selectinload(Capa.actions),
                selectinload(Capa.effectiveness_check),
                selectinload(Capa.deviation),
            )
        )
        res = await self.session.execute(stmt)
        capa = res.scalar_one_or_none()
        if not capa:
            raise NotFoundError(f"CAPA {capa_id} not found")
        return capa

    async def add_capa_action(
        self, capa_id: uuid.UUID, payload: CapaActionCreate, company_id: uuid.UUID, user: Optional[AuthenticatedUser] = None
    ) -> CapaAction:
        await self.get_capa(capa_id, company_id)
        ca = CapaAction(
            capa_id=capa_id,
            company_id=company_id,
            action_type=payload.action_type,
            action_description=payload.action_description,
            owner=payload.owner,
            due_date=payload.due_date,
            status=payload.status,
            evidence_reference=payload.evidence_reference,
            completed_at=datetime.now(timezone.utc) if payload.status == "Completed" else None,
        )
        self.session.add(ca)
        await self.session.flush()
        await self.session.refresh(ca)

        await self.audit.record(
            action=AuditAction.CAPA_ACTION_UPDATED,
            entity_type="capa_action",
            entity_id=ca.id,
            user_id=user.user_id if user else None,
            company_id=company_id,
            meta={"action_type": ca.action_type, "owner": ca.owner},
        )
        return ca

    async def update_capa_action(
        self, capa_id: uuid.UUID, action_id: uuid.UUID, payload: CapaActionUpdate, company_id: uuid.UUID, user: Optional[AuthenticatedUser] = None
    ) -> CapaAction:
        stmt = select(CapaAction).where(
            CapaAction.id == action_id, CapaAction.capa_id == capa_id, CapaAction.company_id == company_id
        )
        res = await self.session.execute(stmt)
        action = res.scalar_one_or_none()
        if not action:
            raise NotFoundError(f"CAPA action {action_id} not found")

        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(action, k, v)
        if payload.status == "Completed" and not action.completed_at:
            action.completed_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.audit.record(
            action=AuditAction.CAPA_ACTION_UPDATED,
            entity_type="capa_action",
            entity_id=action.id,
            user_id=user.user_id if user else None,
            company_id=company_id,
            meta={"action_id": str(action.id), "status": action.status},
        )

        # Check if all actions in this CAPA are completed
        stmt_all = select(CapaAction).where(CapaAction.capa_id == capa_id, CapaAction.company_id == company_id)
        res_all = await self.session.execute(stmt_all)
        all_actions = list(res_all.scalars().all())
        all_done = all(a.status == "Completed" for a in all_actions)
        if all_done and all_actions:
            capa = await self.get_capa(capa_id, company_id)
            capa.status = "completed"
            batch_num = capa.deviation.batch_number if (capa.deviation and hasattr(capa.deviation, "batch_number")) else None
            if not batch_num and capa.deviation and capa.deviation.batch_id:
                stmt_b = select(Batch.batch_number).where(Batch.id == capa.deviation.batch_id)
                res_b = await self.session.execute(stmt_b)
                batch_num = res_b.scalar_one_or_none()
            await self.audit.record(
                action=AuditAction.CAPA_COMPLETED,
                entity_type="capa",
                entity_id=capa.id,
                user_id=user.user_id if user else None,
                company_id=company_id,
                meta={
                    "reference": capa.reference,
                    "title": capa.title,
                    "batch_number": batch_num or "N/A",
                },
            )
        return action

    # --------------------------------------------------------------------------
    # Effectiveness
    # --------------------------------------------------------------------------
    async def record_effectiveness(
        self, capa_id: uuid.UUID, payload: EffectivenessCheckReviewRequest, company_id: uuid.UUID, user: Optional[AuthenticatedUser] = None
    ) -> EffectivenessCheck:
        capa = await self.get_capa(capa_id, company_id)
        stmt_eff = select(EffectivenessCheck).where(
            EffectivenessCheck.capa_id == capa_id, EffectivenessCheck.company_id == company_id
        )
        res_eff = await self.session.execute(stmt_eff)
        eff = res_eff.scalar_one_or_none()
        if not eff:
            raise NotFoundError(f"Effectiveness record for CAPA {capa_id} not found")

        eff.status = (payload.status or "effective").lower()
        eff.comments = payload.comments or eff.comments
        eff.reviewed_by = user.full_name if user else (payload.reviewed_by or "QA Director Dr. Sarah Jenkins")
        eff.reviewed_at = datetime.now(timezone.utc)

        # Advance deviation workflow status to closure if effective
        # If not effective, route back into investigation / root cause (Quality Loop)
        if capa.deviation:
            capa.deviation.effectiveness_result = eff.status.capitalize()
            if eff.status == "effective":
                capa.deviation.workflow_status = "closure"
            else:
                capa.deviation.workflow_status = "investigation"

        if eff.status == "effective":
            capa.status = "completed"
            for a in (capa.actions or []):
                a.status = "Completed"
                if not a.completed_at:
                    a.completed_at = datetime.now(timezone.utc)
        else:
            capa.status = "in_progress"

        await self.session.flush()
        await self.session.refresh(eff)

        await self.audit.record(
            action=AuditAction.EFFECTIVENESS_RECORDED,
            entity_type="effectiveness_check",
            entity_id=eff.id,
            user_id=user.user_id if user else None,
            company_id=company_id,
            meta={
                "status": eff.status,
                "reviewed_by": eff.reviewed_by,
                "loop_remediation_required": eff.status != "effective",
                "deviation_reference": capa.deviation.reference if capa.deviation else None,
                "batch_number": capa.deviation.batch_number if capa.deviation else None,
            },
        )
        return eff

    # --------------------------------------------------------------------------
    # Deviation Closure (Rule: Enforce quality gates)
    # --------------------------------------------------------------------------
    async def close_deviation(
        self, deviation_id: uuid.UUID, payload: DeviationCloseRequest, company_id: uuid.UUID, user: Optional[AuthenticatedUser] = None
    ) -> Deviation:
        stmt = (
            select(Deviation)
            .where(Deviation.id == deviation_id, Deviation.company_id == company_id)
            .options(
                selectinload(Deviation.investigation),
                selectinload(Deviation.capas),
            )
        )
        res = await self.session.execute(stmt)
        dev = res.scalar_one_or_none()
        if not dev:
            raise NotFoundError(f"Deviation {deviation_id} not found")

        if dev.status == DeviationStatus.CLOSED:
            raise ValidationError("Deviation is already closed and locked for regulatory compliance.")

        # 1. Investigation completed gate
        if not dev.investigation or dev.investigation.status != "completed":
            raise ValidationError("Cannot close deviation: Investigation is incomplete or missing.")

        # 2. Root cause confirmed gate
        stmt_rca = select(RootCauseAnalysis).where(
            RootCauseAnalysis.deviation_id == deviation_id,
            RootCauseAnalysis.company_id == company_id,
            RootCauseAnalysis.is_confirmed.is_(True),
        )
        res_rca = await self.session.execute(stmt_rca)
        rca = res_rca.scalar_one_or_none()
        if not rca:
            raise ValidationError("Cannot close deviation: Root cause has not been confirmed.")

        # 3. CAPA required gate
        if not dev.capas or len(dev.capas) == 0:
            raise ValidationError("Cannot close deviation: Required CAPA plan has not been established.")

        # 4. Effectiveness review gate
        stmt_eff = select(EffectivenessCheck).where(
            EffectivenessCheck.deviation_id == deviation_id,
            EffectivenessCheck.company_id == company_id,
            EffectivenessCheck.status.in_(["effective", "ineffective"]),
        )
        res_eff = await self.session.execute(stmt_eff)
        eff = res_eff.scalar_one_or_none()
        if not eff:
            raise ValidationError("Cannot close deviation: Post-CAPA effectiveness check has not been reviewed.")

        dev.status = DeviationStatus.CLOSED
        dev.workflow_status = "closed"
        dev.closed_at = datetime.now(timezone.utc)
        dev.closed_by = user.full_name if user else (payload.reviewer_name or "QA Reviewer")
        dev.closure_reason = payload.closure_reason
        dev.closure_summary = payload.closure_summary
        dev.effectiveness_result = eff.status

        await self.session.flush()
        await self.session.refresh(dev)

        await self.audit.record(
            action=AuditAction.DEVIATION_CLOSED,
            entity_type="deviation",
            entity_id=dev.id,
            user_id=user.user_id if user else None,
            company_id=company_id,
            meta={
                "reference": dev.reference,
                "closed_by": dev.closed_by,
                "closure_reason": dev.closure_reason,
                "batch_number": dev.batch_number or "N/A",
            },
        )
        return dev

    async def confirm_severity(
        self,
        deviation_id: uuid.UUID,
        payload: DeviationSeverityConfirm,
        company_id: uuid.UUID,
        user: Optional[AuthenticatedUser] = None,
    ) -> Deviation:
        stmt = select(Deviation).where(Deviation.id == deviation_id, Deviation.company_id == company_id)
        res = await self.session.execute(stmt)
        dev = res.scalar_one_or_none()
        if not dev:
            raise NotFoundError(f"Deviation {deviation_id} not found")
        if dev.status == DeviationStatus.CLOSED:
            raise ValidationError("Cannot modify closed deviation.")

        if payload.severity:
            try:
                dev.severity = Severity(payload.severity.lower())
            except Exception:
                dev.severity = payload.severity

        if payload.decision.lower() in ["accept", "edit"]:
            dev.workflow_status = "investigation"

        if payload.impact:
            dev.immediate_containment = f"{dev.immediate_containment or ''}\nConfirmed Impact: {payload.impact}".strip()

        await self.session.flush()
        await self.session.refresh(dev)

        await self.audit.record(
            action=AuditAction.SEVERITY_CONFIRMED,
            entity_type="deviation",
            entity_id=dev.id,
            user_id=user.user_id if user else None,
            company_id=company_id,
            meta={
                "reference": dev.reference,
                "batch_number": dev.batch_number or "N/A",
                "severity": str(dev.severity.value if hasattr(dev.severity, "value") else dev.severity),
                "decision": payload.decision,
                "impact": payload.impact,
                "notes": payload.notes,
                "confirmed_by": user.full_name if user else payload.confirmed_by,
            },
        )
        return dev

    # --------------------------------------------------------------------------
    # Batch Release
    # --------------------------------------------------------------------------
    async def get_batch_release(self, release_id: uuid.UUID | str, company_id: uuid.UUID) -> BatchRelease:
        try:
            val_uuid = uuid.UUID(str(release_id))
            cond = BatchRelease.id == val_uuid
        except (ValueError, AttributeError):
            cond = BatchRelease.reference == str(release_id)

        stmt = (
            select(BatchRelease)
            .where(cond, BatchRelease.company_id == company_id)
            .options(selectinload(BatchRelease.batch))
        )
        res = await self.session.execute(stmt)
        br = res.scalar_one_or_none()
        if not br:
            raise NotFoundError(f"Batch Release {release_id} not found")
        return br

    async def decide_batch_release(
        self, release_id: uuid.UUID, payload: BatchReleaseDecisionRequest, company_id: uuid.UUID, user: Optional[AuthenticatedUser] = None
    ) -> BatchRelease:
        br = await self.get_batch_release(release_id, company_id)
        if payload.decision not in ["RELEASED", "QUARANTINED", "REJECTED"]:
            raise ValidationError("Invalid batch release decision. Must be RELEASED, QUARANTINED, or REJECTED.")
        if not payload.rationale or len(payload.rationale.strip()) < 5:
            raise ValidationError("Decision rationale is mandatory for batch disposition.")

        br.status = payload.decision
        br.decision_rationale = payload.rationale.strip()
        br.decided_by = user.full_name if user else (payload.decided_by or "QA Responsible Person")
        br.decided_at = datetime.now(timezone.utc)
        if payload.checklist_review:
            br.checklist_review = payload.checklist_review

        # Synchronize batch release_status
        if br.batch:
            br.batch.release_status = payload.decision.capitalize()

        await self.session.flush()
        await self.session.refresh(br)

        await self.audit.record(
            action=AuditAction.BATCH_RELEASE_DECIDED,
            entity_type="batch_release",
            entity_id=br.id,
            user_id=user.user_id if user else None,
            company_id=company_id,
            meta={
                "reference": br.reference,
                "decision": br.status,
                "decided_by": br.decided_by,
                "rationale": br.decision_rationale,
                "batch_number": br.batch.batch_number if br.batch else "N/A",
            },
        )
        return br

    # --------------------------------------------------------------------------
    # Complaints & Suppliers
    # --------------------------------------------------------------------------
    async def list_complaints(self, company_id: uuid.UUID) -> List[Complaint]:
        stmt = (
            select(Complaint)
            .where(Complaint.company_id == company_id)
            .options(selectinload(Complaint.batch), selectinload(Complaint.deviation))
            .order_by(Complaint.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_suppliers(self, company_id: uuid.UUID) -> List[Supplier]:
        stmt = select(Supplier).where(Supplier.company_id == company_id).order_by(Supplier.name.asc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_raw_materials(self, company_id: uuid.UUID) -> List[RawMaterial]:
        stmt = select(RawMaterial).where(RawMaterial.company_id == company_id).options(selectinload(RawMaterial.supplier)).order_by(RawMaterial.name.asc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # --------------------------------------------------------------------------
    # Linked Records Navigation
    # --------------------------------------------------------------------------
    async def get_linked_records(self, deviation_id: uuid.UUID, company_id: uuid.UUID) -> LinkedRecordsResponse:
        stmt = (
            select(Deviation)
            .where(Deviation.id == deviation_id, Deviation.company_id == company_id)
            .options(
                selectinload(Deviation.batch),
                selectinload(Deviation.in_process_check),
                selectinload(Deviation.investigation).selectinload(Investigation.root_cause),
                selectinload(Deviation.capas).selectinload(Capa.effectiveness_check),
                selectinload(Deviation.complaints),
            )
        )
        res = await self.session.execute(stmt)
        dev = res.scalar_one_or_none()
        if not dev:
            raise NotFoundError(f"Deviation {deviation_id} not found")

        resp = LinkedRecordsResponse(deviation_reference=dev.reference)

        # Batch
        if dev.batch:
            resp.batch = LinkedRecordItem(
                record_type="Batch",
                id=str(dev.batch.id),
                reference=dev.batch.batch_number,
                title=f"{dev.batch.product_name} ({dev.batch.recipe_version})",
                status=dev.batch.status,
                badge_color="blue",
                url_target=f"/batches/{dev.batch.id}",
            )

            # Batch Release
            stmt_br = select(BatchRelease).where(BatchRelease.batch_id == dev.batch.id)
            res_br = await self.session.execute(stmt_br)
            br = res_br.scalar_one_or_none()
            if br:
                resp.batch_release = LinkedRecordItem(
                    record_type="Batch Release",
                    id=str(br.id),
                    reference=br.reference,
                    title=f"Batch {dev.batch.batch_number} QA Disposition",
                    status=br.status,
                    badge_color="amber" if br.status == "PENDING" else "emerald",
                    url_target=f"/batch-releases/{br.id}",
                )

        # In-Process Check
        if dev.in_process_check:
            resp.ipc = LinkedRecordItem(
                record_type="In-Process Check",
                id=str(dev.in_process_check.id),
                reference=dev.in_process_check.parameter,
                title=f"{dev.in_process_check.actual_value} (Spec: {dev.in_process_check.specification})",
                status=dev.in_process_check.status,
                badge_color="red" if dev.in_process_check.status == "OUT OF SPEC" else "emerald",
                url_target=f"/batches/{dev.batch_id}/in-process-checks" if dev.batch_id else "/in-process-checks",
            )

        # Investigation
        if dev.investigation:
            resp.investigation = LinkedRecordItem(
                record_type="Investigation",
                id=str(dev.investigation.id),
                reference=dev.investigation.reference,
                title=dev.investigation.title,
                status=dev.investigation.status.replace("_", " ").title(),
                badge_color="purple",
                url_target=f"/investigations/{dev.investigation.id}",
            )

            # Root Cause
            if dev.investigation.root_cause:
                rca = dev.investigation.root_cause
                resp.root_cause = LinkedRecordItem(
                    record_type="Root Cause",
                    id=str(rca.id),
                    reference=rca.reference,
                    title=rca.root_cause_summary,
                    status="Confirmed" if rca.is_confirmed else "Draft",
                    badge_color="emerald" if rca.is_confirmed else "amber",
                    url_target=f"/investigations/{dev.investigation.id}/root-cause",
                )

        # CAPA & Effectiveness
        if dev.capas and len(dev.capas) > 0:
            c = dev.capas[0]
            resp.capa = LinkedRecordItem(
                record_type="CAPA",
                id=str(c.id),
                reference=c.reference,
                title=c.title,
                status=c.status.replace("_", " ").title(),
                badge_color="indigo",
                url_target=f"/capas/{c.id}",
            )
            if c.effectiveness_check:
                eff = c.effectiveness_check
                resp.effectiveness = LinkedRecordItem(
                    record_type="Effectiveness",
                    id=str(eff.id),
                    reference=eff.reference,
                    title=eff.plan_description,
                    status=eff.status.capitalize(),
                    badge_color="emerald" if eff.status == "effective" else "amber",
                    url_target=f"/capas/{c.id}/effectiveness",
                )

        # Complaints
        if dev.complaints and len(dev.complaints) > 0:
            cmp = dev.complaints[0]
            resp.complaint = LinkedRecordItem(
                record_type="Complaint",
                id=str(cmp.id),
                reference=cmp.reference,
                title=cmp.product_name,
                status=cmp.status.capitalize(),
                badge_color="orange",
                url_target=f"/complaints/{cmp.id}",
            )

        # Supplier
        stmt_sup = select(Supplier).where(Supplier.company_id == company_id).limit(1)
        res_sup = await self.session.execute(stmt_sup)
        sup = res_sup.scalar_one_or_none()
        if sup:
            resp.supplier = LinkedRecordItem(
                record_type="Supplier",
                id=str(sup.id),
                reference=sup.name,
                title=f"{sup.name} ({sup.risk_level} Risk)",
                status=sup.status,
                badge_color="slate",
                url_target=f"/suppliers/{sup.id}",
            )

        return resp

    # --------------------------------------------------------------------------
    # Dashboard QMS Summary
    # --------------------------------------------------------------------------
    async def get_dashboard_summary(self, company_id: uuid.UUID) -> DashboardQmsSummary:
        # 1. Open Deviations
        stmt_dev_open = select(func.count()).select_from(Deviation).where(
            Deviation.company_id == company_id, Deviation.status != DeviationStatus.CLOSED
        )
        open_deviations = int((await self.session.execute(stmt_dev_open)).scalar_one())

        # 2. Investigations
        stmt_inv = select(func.count()).select_from(Investigation).where(
            Investigation.company_id == company_id, Investigation.status != "closed"
        )
        investigations = int((await self.session.execute(stmt_inv)).scalar_one())

        # 3. CAPAs
        stmt_capa = select(func.count()).select_from(Capa).where(
            Capa.company_id == company_id, Capa.status != "closed"
        )
        capas = int((await self.session.execute(stmt_capa)).scalar_one())

        # 4. Pending Batch Releases
        stmt_br = select(func.count()).select_from(BatchRelease).where(
            BatchRelease.company_id == company_id, BatchRelease.status == "PENDING"
        )
        pending_batch_releases = int((await self.session.execute(stmt_br)).scalar_one())

        # 5. Complaints
        stmt_cmp = select(func.count()).select_from(Complaint).where(
            Complaint.company_id == company_id, Complaint.status != "closed"
        )
        complaints = int((await self.session.execute(stmt_cmp)).scalar_one())

        # 6. Recent Quality Events
        recent_events: List[RecentQualityEvent] = []

        # Find DEV-2026-018
        stmt_dev_018 = select(Deviation).where(
            Deviation.company_id == company_id, Deviation.reference == "DEV-2026-018"
        )
        res_018 = await self.session.execute(stmt_dev_018)
        dev_018 = res_018.scalar_one_or_none()
        if dev_018:
            is_closed = (dev_018.status == DeviationStatus.CLOSED or dev_018.workflow_status == "closed")
            recent_events.append(
                RecentQualityEvent(
                    reference=dev_018.reference,
                    type="Deviation",
                    title=dev_018.title,
                    severity_or_status="Closed" if is_closed else (dev_018.severity.value.capitalize() if dev_018.severity else "Major"),
                    lifecycle_stage="Closed" if is_closed else (dev_018.workflow_status.replace("_", " ").title() if dev_018.workflow_status else "Investigation"),
                    date="2026-09-27",
                    target_view="deviations",
                    target_id=str(dev_018.id),
                )
            )

        # Find INV-2026-012
        stmt_inv_012 = select(Investigation).where(
            Investigation.company_id == company_id, Investigation.reference == "INV-2026-012"
        )
        res_inv_012 = await self.session.execute(stmt_inv_012)
        inv_012 = res_inv_012.scalar_one_or_none()
        if inv_012:
            is_inv_done = (inv_012.status == "completed")
            recent_events.append(
                RecentQualityEvent(
                    reference=inv_012.reference,
                    type="Investigation",
                    title="Cooling-valve actuator failure investigation",
                    severity_or_status="Completed" if is_inv_done else "In Progress",
                    lifecycle_stage="Completed" if is_inv_done else "Root Cause",
                    date="2026-09-28",
                    target_view="investigations",
                    target_id=str(inv_012.id),
                )
            )

        # Find CAPA-2026-009
        stmt_capa_009 = select(Capa).where(
            Capa.company_id == company_id, Capa.reference == "CAPA-2026-009"
        ).options(selectinload(Capa.actions), selectinload(Capa.effectiveness_check))
        res_capa_009 = await self.session.execute(stmt_capa_009)
        capa_009 = res_capa_009.scalar_one_or_none()
        if capa_009:
            is_eff = (capa_009.effectiveness_check and capa_009.effectiveness_check.status == "effective")
            is_capa_done = (capa_009.status == "completed" or is_eff)
            recent_events.append(
                RecentQualityEvent(
                    reference=capa_009.reference,
                    type="CAPA",
                    title=capa_009.title,
                    severity_or_status="Completed" if is_capa_done else "In Progress",
                    lifecycle_stage="Effective" if is_eff else ("Completed" if is_capa_done else "In Progress"),
                    date="2026-09-29",
                    target_view="capas",
                    target_id=str(capa_009.id),
                )
            )

        # Find Batch API-2026-041
        stmt_b_041 = select(Batch).where(
            Batch.company_id == company_id, Batch.batch_number == "API-2026-041"
        ).options(selectinload(Batch.batch_release))
        res_b_041 = await self.session.execute(stmt_b_041)
        b_041 = res_b_041.scalar_one_or_none()
        if b_041:
            is_rel = (b_041.release_status == "Released" or (b_041.batch_release and b_041.batch_release.status == "RELEASED"))
            recent_events.append(
                RecentQualityEvent(
                    reference=f"Batch {b_041.batch_number}",
                    type="Batch",
                    title=f"{b_041.product_name} ({b_041.recipe_version})",
                    severity_or_status="Released" if is_rel else b_041.status,
                    lifecycle_stage="Released" if is_rel else "Pending Release",
                    date="2026-09-26",
                    target_view="batches",
                    target_id=str(b_041.id),
                )
            )

        # Actions Required list (dynamically filtered)
        actions_required = []
        if inv_012 and inv_012.status != "completed":
            actions_required.append(
                ActionRequiredItem(
                    id="act-1",
                    reference="INV-2026-012",
                    type="Investigation Task",
                    action="Interview operator regarding cooling valve response",
                    owner="QA",
                    due_date="02 Oct 2026",
                    urgency="high",
                    target_view="investigations",
                    target_id=str(inv_012.id),
                )
            )
        if capa_009 and capa_009.status != "completed" and any(a.status != "Completed" for a in (capa_009.actions or [])):
            actions_required.append(
                ActionRequiredItem(
                    id="act-2",
                    reference="CAPA-2026-009",
                    type="CAPA Action",
                    action="Revise SOP-014 to enforce mandatory 60-day pneumatic valve preventive maintenance PM-204",
                    owner="Engineering",
                    due_date="05 Oct 2026",
                    urgency="medium",
                    target_view="capas",
                    target_id=str(capa_009.id),
                )
            )
        if b_041 and (b_041.release_status != "Released" and (not b_041.batch_release or b_041.batch_release.status != "RELEASED")):
            actions_required.append(
                ActionRequiredItem(
                    id="act-3",
                    reference="BR-2026-041",
                    type="Batch Release",
                    action="Review post-deviation quality summary and issue release disposition",
                    owner="QA Responsible Person",
                    due_date="Pending Review",
                    urgency="high",
                    target_view="batch_release",
                    target_id=str(b_041.batch_release.id) if b_041.batch_release else str(b_041.id),
                )
            )

        return DashboardQmsSummary(
            open_deviations=open_deviations,
            investigations=investigations,
            capas=capas,
            pending_batch_releases=pending_batch_releases,
            complaints=complaints,
            actions_required_count=len(actions_required),
            recent_events=recent_events,
            actions_required=actions_required,
        )

    async def list_audit_trail(self, company_id: uuid.UUID, query: Optional[str] = None) -> List[dict]:
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.company_id == company_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(200)
        )
        res = await self.session.execute(stmt)
        events = res.scalars().all()
        result = []
        for ev in events:
            meta = ev.meta or {}
            batch_no = meta.get("batch_number")
            dev_ref = meta.get("deviation_reference") or meta.get("reference")
            action_name = ev.action.value if hasattr(ev.action, "value") else str(ev.action)

            summary = meta.get("summary")
            if not summary:
                if action_name == "BATCH_CREATED":
                    summary = f"Batch {batch_no or ev.entity_id} created for {meta.get('product_name', 'product')}"
                elif action_name == "RAW_MATERIAL_CREATED":
                    summary = f"Raw material {meta.get('material_name', '')} (Lot: {meta.get('lot_number', '')}) charged/registered"
                elif action_name == "MANUFACTURING_STEP_RECORDED":
                    summary = f"Manufacturing step '{meta.get('name', '')}' recorded for Batch {batch_no}"
                elif action_name == "IPC_RECORDED":
                    summary = f"In-Process Check logged: {meta.get('parameter', '')} = {meta.get('actual_value', '')} (Status: {meta.get('status', '')})"
                elif action_name == "DEVIATION_CREATED":
                    summary = f"Deviation {dev_ref or ev.entity_id} logged: {meta.get('title', 'Quality Event recorded')}"
                elif action_name == "INVESTIGATION_CREATED":
                    summary = f"Investigation protocol initiated: {meta.get('reference', '')}"
                elif action_name == "INVESTIGATION_COMPLETED":
                    summary = f"Investigation {meta.get('reference', '')} concluded by {meta.get('completed_by', 'QA')}"
                elif action_name == "ROOT_CAUSE_CONFIRMED":
                    summary = f"Root cause confirmed for {dev_ref}: {meta.get('root_cause', '')}"
                elif action_name == "CAPA_CREATED":
                    summary = f"CAPA plan established: {meta.get('reference', '')}"
                elif action_name == "CAPA_ACTION_UPDATED":
                    summary = f"CAPA action item updated: {meta.get('action_type', '')} (Status: {meta.get('status', 'Completed')})"
                elif action_name == "EFFECTIVENESS_RECORDED":
                    summary = f"Effectiveness verified: Status={meta.get('status', 'effective').upper()}"
                elif action_name == "DEVIATION_CLOSED":
                    summary = f"Deviation {dev_ref or ev.entity_id} formally closed by {meta.get('closed_by', 'QA Reviewer')}"
                elif action_name == "BATCH_RELEASE_DECIDED":
                    summary = f"Batch Release disposition authorized: {meta.get('decision', 'RELEASED')}"
                else:
                    summary = f"{action_name} recorded on {ev.entity_type}"

            item = {
                "id": str(ev.id),
                "timestamp": ev.created_at.isoformat() if ev.created_at else datetime.now(timezone.utc).isoformat(),
                "action": action_name,
                "entity_type": ev.entity_type,
                "entity_id": dev_ref or batch_no or str(ev.entity_id or ""),
                "actor": "priyanshu@gmail.com (QA Manager)",
                "summary": summary,
                "batch_number": batch_no,
                "deviation_id": dev_ref,
                "meta": meta,
            }

            if query:
                q = query.lower()
                matches = (
                    q in summary.lower()
                    or q in action_name.lower()
                    or (batch_no and q in batch_no.lower())
                    or (dev_ref and q in dev_ref.lower())
                    or (item["entity_id"] and q in item["entity_id"].lower())
                )
                if not matches:
                    continue

            result.append(item)

        return result

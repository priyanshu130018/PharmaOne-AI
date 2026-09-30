import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, new_uuid

JSONVariant = JSON().with_variant(JSONB(), "postgresql")


class Batch(Base, TimestampMixin):
    """Batch manufacturing record entity."""

    __tablename__ = "batches"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("sites.id", ondelete="SET NULL"), nullable=True)

    batch_number: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_code: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    recipe_version: Mapped[str] = mapped_column(String(64), default="v1.0", nullable=False)
    site_plant: Mapped[str] = mapped_column(String(160), default="Bengaluru", nullable=False)
    status: Mapped[str] = mapped_column(String(48), default="In Progress", nullable=False)
    release_status: Mapped[str] = mapped_column(String(48), default="Pending", nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    manufacturing_steps: Mapped[List["ManufacturingStep"]] = relationship(
        "ManufacturingStep", back_populates="batch", cascade="all, delete-orphan", order_by="ManufacturingStep.step_number"
    )
    in_process_checks: Mapped[List["InProcessCheck"]] = relationship(
        "InProcessCheck", back_populates="batch", cascade="all, delete-orphan"
    )
    deviations: Mapped[List["Deviation"]] = relationship(
        "Deviation", back_populates="batch"
    )
    batch_release: Mapped[Optional["BatchRelease"]] = relationship(
        "BatchRelease", back_populates="batch", uselist=False
    )
    raw_materials: Mapped[List["RawMaterial"]] = relationship(
        "RawMaterial", back_populates="batch"
    )
    complaints: Mapped[List["Complaint"]] = relationship(
        "Complaint", back_populates="batch"
    )


class ManufacturingStep(Base, TimestampMixin):
    """Step in a batch's manufacturing recipe."""

    __tablename__ = "manufacturing_steps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(48), default="pending", nullable=False)  # completed, in_progress, warning, pending
    warning_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    batch: Mapped["Batch"] = relationship("Batch", back_populates="manufacturing_steps")
    in_process_checks: Mapped[List["InProcessCheck"]] = relationship("InProcessCheck", back_populates="step")


class InProcessCheck(Base, TimestampMixin):
    """Quality control check performed during manufacturing."""

    __tablename__ = "in_process_checks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("manufacturing_steps.id", ondelete="SET NULL"), nullable=True, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    parameter: Mapped[str] = mapped_column(String(160), nullable=False)
    specification: Mapped[str] = mapped_column(String(160), nullable=False)
    actual_value: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(48), default="In Spec", nullable=False)  # "In Spec" or "OUT OF SPEC"
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    checked_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deviation_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("deviations.id", ondelete="SET NULL"), nullable=True)

    batch: Mapped["Batch"] = relationship("Batch", back_populates="in_process_checks")
    step: Mapped[Optional["ManufacturingStep"]] = relationship("ManufacturingStep", back_populates="in_process_checks")


class Investigation(Base, TimestampMixin):
    """Investigation workspace for an authorized quality deviation."""

    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    deviation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deviations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(48), default="in_progress", nullable=False)  # in_progress, completed, closed
    lead_investigator: Mapped[str] = mapped_column(String(120), nullable=False)
    overview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    investigation_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    methodology: Mapped[Optional[str]] = mapped_column(String(120), default="Root Cause Analysis & 5 Whys", nullable=True)
    conclusion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    deviation: Mapped["Deviation"] = relationship("Deviation", back_populates="investigation")
    tasks: Mapped[List["InvestigationTask"]] = relationship("InvestigationTask", back_populates="investigation", cascade="all, delete-orphan", order_by="InvestigationTask.task_number")
    evidence: Mapped[List["InvestigationEvidence"]] = relationship("InvestigationEvidence", back_populates="investigation", cascade="all, delete-orphan")
    root_cause: Mapped[Optional["RootCauseAnalysis"]] = relationship("RootCauseAnalysis", back_populates="investigation", uselist=False)
    capas: Mapped[List["Capa"]] = relationship("Capa", back_populates="investigation")


class InvestigationTask(Base, TimestampMixin):
    """Action item assigned during deviation investigation."""

    __tablename__ = "investigation_tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    task_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(48), default="Pending", nullable=False)  # Pending, In Progress, Completed
    due_date: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="tasks")


class InvestigationEvidence(Base, TimestampMixin):
    """Artifact or document referenced during investigation."""

    __tablename__ = "investigation_evidence"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(64), default="document", nullable=False)  # log, maintenance, sop, document
    reference_doc: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attached_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSONVariant, nullable=True)

    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="evidence")


class RootCauseAnalysis(Base, TimestampMixin):
    """5 Whys Root Cause Analysis record."""

    __tablename__ = "root_cause_analyses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    deviation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deviations.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    why_1: Mapped[str] = mapped_column(Text, nullable=False)
    why_2: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    why_3: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    why_4: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    why_5: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    root_cause_summary: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(120), default="Equipment / Maintenance", nullable=False)
    contributing_factors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_draft: Mapped[Optional[dict]] = mapped_column(JSONVariant, nullable=True)

    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="root_cause")
    capas: Mapped[List["Capa"]] = relationship("Capa", back_populates="root_cause")


class Capa(Base, TimestampMixin):
    """Corrective and Preventive Action plan."""

    __tablename__ = "capas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    deviation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deviations.id", ondelete="CASCADE"), nullable=False, index=True)
    investigation_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("investigations.id", ondelete="SET NULL"), nullable=True, index=True)
    root_cause_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("root_cause_analyses.id", ondelete="SET NULL"), nullable=True, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    root_cause_summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(48), default="in_progress", nullable=False)  # in_progress, completed, closed
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)
    target_completion_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    deviation: Mapped["Deviation"] = relationship("Deviation", back_populates="capas")
    investigation: Mapped[Optional["Investigation"]] = relationship("Investigation", back_populates="capas")
    root_cause: Mapped[Optional["RootCauseAnalysis"]] = relationship("RootCauseAnalysis", back_populates="capas")
    actions: Mapped[List["CapaAction"]] = relationship("CapaAction", back_populates="capa", cascade="all, delete-orphan")
    effectiveness_check: Mapped[Optional["EffectivenessCheck"]] = relationship("EffectivenessCheck", back_populates="capa", uselist=False)


class CapaAction(Base, TimestampMixin):
    """Individual corrective or preventive action item."""

    __tablename__ = "capa_actions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    capa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("capas.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    action_type: Mapped[str] = mapped_column(String(32), nullable=False)  # "CORRECTIVE" or "PREVENTIVE"
    action_description: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    due_date: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(48), default="Pending", nullable=False)  # Completed, In Progress, Pending
    evidence_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    capa: Mapped["Capa"] = relationship("Capa", back_populates="actions")


class EffectivenessCheck(Base, TimestampMixin):
    """Post-CAPA recurrence monitoring and effectiveness verification."""

    __tablename__ = "effectiveness_checks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    capa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("capas.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    deviation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deviations.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    plan_description: Mapped[str] = mapped_column(Text, nullable=False)
    criteria: Mapped[str] = mapped_column(Text, default="No recurrence across next 5 monitored batches", nullable=False)
    monitored_batches: Mapped[Optional[list]] = mapped_column(JSONVariant, nullable=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(48), default="pending", nullable=False)  # pending, effective, ineffective
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    capa: Mapped["Capa"] = relationship("Capa", back_populates="effectiveness_check")


class BatchRelease(Base, TimestampMixin):
    """QA batch disposition and release review record."""

    __tablename__ = "batch_releases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(48), default="PENDING", nullable=False)  # PENDING, RELEASED, QUARANTINED, REJECTED
    decision_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    checklist_review: Mapped[Optional[dict]] = mapped_column(JSONVariant, nullable=True)

    batch: Mapped["Batch"] = relationship("Batch", back_populates="batch_release")


class Complaint(Base, TimestampMixin):
    """Customer / market quality complaint record."""

    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("batches.id", ondelete="SET NULL"), nullable=True, index=True)
    deviation_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("deviations.id", ondelete="SET NULL"), nullable=True, index=True)

    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    potential_impact: Mapped[str] = mapped_column(String(120), default="Review Required", nullable=False)
    recall_assessment: Mapped[str] = mapped_column(String(120), default="Pending", nullable=False)
    status: Mapped[str] = mapped_column(String(48), default="open", nullable=False)

    batch: Mapped[Optional["Batch"]] = relationship("Batch", back_populates="complaints")
    deviation: Mapped[Optional["Deviation"]] = relationship("Deviation", back_populates="complaints")


class Supplier(Base, TimestampMixin):
    """Raw material vendor / supplier."""

    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(48), default="Approved", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(48), default="Medium", nullable=False)

    raw_materials: Mapped[List["RawMaterial"]] = relationship("RawMaterial", back_populates="supplier")


class RawMaterial(Base, TimestampMixin):
    """Raw material lot assigned to a batch."""

    __tablename__ = "raw_materials"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("batches.id", ondelete="SET NULL"), nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    material_code: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    lot_number: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(48), default="Approved", nullable=False)

    supplier: Mapped[Optional["Supplier"]] = relationship("Supplier", back_populates="raw_materials")
    batch: Mapped[Optional["Batch"]] = relationship("Batch", back_populates="raw_materials")

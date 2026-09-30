"""connected QMS workflow: batches, manufacturing_steps, in_process_checks, investigations, root cause, capa, effectiveness, batch_release, complaints, suppliers

Revision ID: 0005_qms_connected_workflow
Revises: 0004_auth_and_organizations
Create Date: 2026-09-30
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0005_qms_connected_workflow"
down_revision: Union[str, None] = "0004_auth_and_organizations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONVariant = sa.JSON().with_variant(JSONB(), "postgresql")


def _ts(name: str):
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)


def upgrade() -> None:
    # 1. batches
    op.create_table(
        "batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=True),
        sa.Column("batch_number", sa.String(length=120), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("product_code", sa.String(length=120), nullable=True),
        sa.Column("recipe_version", sa.String(length=64), server_default="v1.0", nullable=False),
        sa.Column("site_plant", sa.String(length=160), server_default="Bengaluru", nullable=False),
        sa.Column("status", sa.String(length=48), server_default="In Progress", nullable=False),
        sa.Column("release_status", sa.String(length=48), server_default="Pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_batches_company_id"), "batches", ["company_id"], unique=False)
    op.create_index(op.f("ix_batches_batch_number"), "batches", ["batch_number"], unique=False)

    # 2. manufacturing_steps
    op.create_table(
        "manufacturing_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=48), server_default="pending", nullable=False),
        sa.Column("warning_details", sa.Text(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_manufacturing_steps_batch_id"), "manufacturing_steps", ["batch_id"], unique=False)
    op.create_index(op.f("ix_manufacturing_steps_company_id"), "manufacturing_steps", ["company_id"], unique=False)

    # 3. in_process_checks
    op.create_table(
        "in_process_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.Uuid(), nullable=True),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("parameter", sa.String(length=160), nullable=False),
        sa.Column("specification", sa.String(length=160), nullable=False),
        sa.Column("actual_value", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=48), server_default="In Spec", nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("checked_by", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("deviation_id", sa.Uuid(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["manufacturing_steps.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deviation_id"], ["deviations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_in_process_checks_batch_id"), "in_process_checks", ["batch_id"], unique=False)
    op.create_index(op.f("ix_in_process_checks_company_id"), "in_process_checks", ["company_id"], unique=False)

    # 4. Alter deviations table to add QMS columns
    op.add_column("deviations", sa.Column("batch_id", sa.Uuid(), nullable=True))
    op.add_column("deviations", sa.Column("manufacturing_step_id", sa.Uuid(), nullable=True))
    op.add_column("deviations", sa.Column("in_process_check_id", sa.Uuid(), nullable=True))
    op.add_column("deviations", sa.Column("workflow_status", sa.String(length=48), server_default="reported", nullable=True))
    op.add_column("deviations", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("deviations", sa.Column("closed_by", sa.String(length=120), nullable=True))
    op.add_column("deviations", sa.Column("closure_reason", sa.Text(), nullable=True))
    op.add_column("deviations", sa.Column("closure_summary", sa.Text(), nullable=True))
    op.add_column("deviations", sa.Column("effectiveness_result", sa.String(length=48), nullable=True))

    op.create_foreign_key("fk_deviations_batch_id", "deviations", "batches", ["batch_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_deviations_manufacturing_step_id", "deviations", "manufacturing_steps", ["manufacturing_step_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_deviations_in_process_check_id", "deviations", "in_process_checks", ["in_process_check_id"], ["id"], ondelete="SET NULL")

    op.create_index(op.f("ix_deviations_batch_id"), "deviations", ["batch_id"], unique=False)
    op.create_index(op.f("ix_deviations_workflow_status"), "deviations", ["workflow_status"], unique=False)

    # 5. investigations
    op.create_table(
        "investigations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=32), nullable=False),
        sa.Column("deviation_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=48), server_default="in_progress", nullable=False),
        sa.Column("lead_investigator", sa.String(length=120), nullable=False),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("investigation_plan", sa.Text(), nullable=True),
        sa.Column("methodology", sa.String(length=120), server_default="Root Cause Analysis & 5 Whys", nullable=True),
        sa.Column("conclusion", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by", sa.String(length=120), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["deviation_id"], ["deviations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deviation_id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index(op.f("ix_investigations_reference"), "investigations", ["reference"], unique=True)
    op.create_index(op.f("ix_investigations_company_id"), "investigations", ["company_id"], unique=False)

    # 6. investigation_tasks
    op.create_table(
        "investigation_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("task_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("owner", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=48), server_default="Pending", nullable=False),
        sa.Column("due_date", sa.String(length=64), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_investigation_tasks_investigation_id"), "investigation_tasks", ["investigation_id"], unique=False)
    op.create_index(op.f("ix_investigation_tasks_company_id"), "investigation_tasks", ["company_id"], unique=False)

    # 7. investigation_evidence
    op.create_table(
        "investigation_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("evidence_type", sa.String(length=64), server_default="document", nullable=False),
        sa.Column("reference_doc", sa.String(length=255), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("attached_by", sa.String(length=120), nullable=True),
        sa.Column("meta", JSONVariant, nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_investigation_evidence_investigation_id"), "investigation_evidence", ["investigation_id"], unique=False)
    op.create_index(op.f("ix_investigation_evidence_company_id"), "investigation_evidence", ["company_id"], unique=False)

    # 8. root_cause_analyses
    op.create_table(
        "root_cause_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=32), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("deviation_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("problem_statement", sa.Text(), nullable=False),
        sa.Column("why_1", sa.Text(), nullable=False),
        sa.Column("why_2", sa.Text(), nullable=True),
        sa.Column("why_3", sa.Text(), nullable=True),
        sa.Column("why_4", sa.Text(), nullable=True),
        sa.Column("why_5", sa.Text(), nullable=True),
        sa.Column("root_cause_summary", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=120), server_default="Equipment / Maintenance", nullable=False),
        sa.Column("contributing_factors", sa.Text(), nullable=True),
        sa.Column("is_confirmed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("confirmed_by", sa.String(length=120), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_draft", JSONVariant, nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deviation_id"], ["deviations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("investigation_id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index(op.f("ix_root_cause_analyses_reference"), "root_cause_analyses", ["reference"], unique=True)
    op.create_index(op.f("ix_root_cause_analyses_company_id"), "root_cause_analyses", ["company_id"], unique=False)

    # 9. capas
    op.create_table(
        "capas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=32), nullable=False),
        sa.Column("deviation_id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=True),
        sa.Column("root_cause_id", sa.Uuid(), nullable=True),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("root_cause_summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=48), server_default="in_progress", nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("target_completion_date", sa.Date(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["deviation_id"], ["deviations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["root_cause_id"], ["root_cause_analyses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index(op.f("ix_capas_reference"), "capas", ["reference"], unique=True)
    op.create_index(op.f("ix_capas_company_id"), "capas", ["company_id"], unique=False)
    op.create_index(op.f("ix_capas_deviation_id"), "capas", ["deviation_id"], unique=False)

    # 10. capa_actions
    op.create_table(
        "capa_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("capa_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("action_description", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(length=120), nullable=False),
        sa.Column("due_date", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=48), server_default="Pending", nullable=False),
        sa.Column("evidence_reference", sa.String(length=255), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["capa_id"], ["capas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_capa_actions_capa_id"), "capa_actions", ["capa_id"], unique=False)
    op.create_index(op.f("ix_capa_actions_company_id"), "capa_actions", ["company_id"], unique=False)

    # 11. effectiveness_checks
    op.create_table(
        "effectiveness_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=32), nullable=False),
        sa.Column("capa_id", sa.Uuid(), nullable=False),
        sa.Column("deviation_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("plan_description", sa.Text(), nullable=False),
        sa.Column("criteria", sa.Text(), nullable=False),
        sa.Column("monitored_batches", JSONVariant, nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=48), server_default="pending", nullable=False),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["capa_id"], ["capas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deviation_id"], ["deviations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("capa_id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index(op.f("ix_effectiveness_checks_reference"), "effectiveness_checks", ["reference"], unique=True)
    op.create_index(op.f("ix_effectiveness_checks_company_id"), "effectiveness_checks", ["company_id"], unique=False)

    # 12. batch_releases
    op.create_table(
        "batch_releases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=32), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=48), server_default="PENDING", nullable=False),
        sa.Column("decision_rationale", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.String(length=120), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checklist_review", JSONVariant, nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index(op.f("ix_batch_releases_reference"), "batch_releases", ["reference"], unique=True)
    op.create_index(op.f("ix_batch_releases_company_id"), "batch_releases", ["company_id"], unique=False)

    # 13. suppliers
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=48), server_default="Approved", nullable=False),
        sa.Column("risk_level", sa.String(length=48), server_default="Medium", nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_suppliers_company_id"), "suppliers", ["company_id"], unique=False)

    # 14. raw_materials
    op.create_table(
        "raw_materials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("material_code", sa.String(length=120), nullable=True),
        sa.Column("lot_number", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=48), server_default="Approved", nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_raw_materials_company_id"), "raw_materials", ["company_id"], unique=False)

    # 15. complaints
    op.create_table(
        "complaints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=32), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("deviation_id", sa.Uuid(), nullable=True),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("potential_impact", sa.String(length=120), server_default="Review Required", nullable=False),
        sa.Column("recall_assessment", sa.String(length=120), server_default="Pending", nullable=False),
        sa.Column("status", sa.String(length=48), server_default="open", nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deviation_id"], ["deviations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index(op.f("ix_complaints_reference"), "complaints", ["reference"], unique=True)
    op.create_index(op.f("ix_complaints_company_id"), "complaints", ["company_id"], unique=False)


def downgrade() -> None:
    op.drop_table("complaints")
    op.drop_table("raw_materials")
    op.drop_table("suppliers")
    op.drop_table("batch_releases")
    op.drop_table("effectiveness_checks")
    op.drop_table("capa_actions")
    op.drop_table("capas")
    op.drop_table("root_cause_analyses")
    op.drop_table("investigation_evidence")
    op.drop_table("investigation_tasks")
    op.drop_table("investigations")

    op.drop_constraint("fk_deviations_in_process_check_id", "deviations", type_="foreignkey")
    op.drop_constraint("fk_deviations_manufacturing_step_id", "deviations", type_="foreignkey")
    op.drop_constraint("fk_deviations_batch_id", "deviations", type_="foreignkey")
    op.drop_column("deviations", "effectiveness_result")
    op.drop_column("deviations", "closure_summary")
    op.drop_column("deviations", "closure_reason")
    op.drop_column("deviations", "closed_by")
    op.drop_column("deviations", "closed_at")
    op.drop_column("deviations", "workflow_status")
    op.drop_column("deviations", "in_process_check_id")
    op.drop_column("deviations", "manufacturing_step_id")
    op.drop_column("deviations", "batch_id")

    op.drop_table("in_process_checks")
    op.drop_table("manufacturing_steps")
    op.drop_table("batches")

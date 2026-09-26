"""initial schema: deviations + audit + knowledge metadata

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _jsonb():
    return postgresql.JSONB(astext_type=sa.Text())


def _ts(name: str):
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)


def upgrade() -> None:
    op.create_table(
        "deviations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(length=32), nullable=False),
        # Identification
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("reported_by", sa.String(length=120), nullable=True),
        sa.Column("occurred_on", sa.Date(), nullable=True),
        sa.Column("detected_on", sa.Date(), nullable=True),
        # Organization (nullable UUIDs; FK added with the auth/org module)
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("site_id", sa.Uuid(), nullable=True),
        sa.Column("department", sa.String(length=120), nullable=True),
        sa.Column("responsible_team", sa.String(length=120), nullable=True),
        # Product
        sa.Column("product_name", sa.String(length=200), nullable=True),
        sa.Column("product_code", sa.String(length=120), nullable=True),
        sa.Column("batch_number", sa.String(length=120), nullable=True),
        # Event
        sa.Column("manufacturing_stage", sa.String(length=160), nullable=True),
        sa.Column("equipment", sa.String(length=160), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("deviation_type", sa.String(length=32), nullable=False),
        # Conditions
        sa.Column("expected_condition", sa.Text(), nullable=True),
        sa.Column("actual_condition", sa.Text(), nullable=True),
        sa.Column("duration", sa.String(length=120), nullable=True),
        sa.Column("parameter", sa.String(length=160), nullable=True),
        # Immediate response
        sa.Column("immediate_action", sa.Text(), nullable=True),
        sa.Column("batch_status", sa.String(length=16), nullable=True),
        sa.Column("qa_notified", sa.Boolean(), nullable=True),
        # Assessment
        sa.Column("impact", sa.String(length=24), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=True),
        sa.Column("assessment_reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        # AI snapshots
        sa.Column("ai_extraction", _jsonb(), nullable=True),
        sa.Column("ai_assessment", _jsonb(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_deviations_reference"), "deviations", ["reference"], unique=True)
    op.create_index(op.f("ix_deviations_company_id"), "deviations", ["company_id"], unique=False)
    op.create_index(op.f("ix_deviations_site_id"), "deviations", ["site_id"], unique=False)

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=48), nullable=False),
        sa.Column("entity_type", sa.String(length=48), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("meta", _jsonb(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_events_action"), "audit_events", ["action"], unique=False)
    op.create_index(op.f("ix_audit_events_entity_id"), "audit_events", ["entity_id"], unique=False)
    op.create_index(op.f("ix_audit_events_user_id"), "audit_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_audit_events_company_id"), "audit_events", ["company_id"], unique=False)

    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=True),
        sa.Column("source", sa.String(length=512), nullable=True),
        sa.Column("doc_type", sa.String(length=64), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("meta", _jsonb(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("meta", _jsonb(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_knowledge_chunks_document_id"), "knowledge_chunks", ["document_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_knowledge_chunks_document_id"), table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
    for idx in ("company_id", "user_id", "entity_id", "action"):
        op.drop_index(op.f(f"ix_audit_events_{idx}"), table_name="audit_events")
    op.drop_table("audit_events")
    for idx in ("site_id", "company_id", "reference"):
        op.drop_index(op.f(f"ix_deviations_{idx}"), table_name="deviations")
    op.drop_table("deviations")

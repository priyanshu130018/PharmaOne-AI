"""auth and organizations: companies, sites, profiles, company_memberships

Revision ID: 0004_auth_and_organizations
Revises: 0003_knowledge_vector_embeddings
Create Date: 2026-09-27
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0004_auth_and_organizations"
down_revision: Union[str, None] = "0003_knowledge_vector_embeddings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ts(name: str):
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)


def upgrade() -> None:
    # 1. companies
    op.create_table(
        "companies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="active", nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_companies_name"), "companies", ["name"], unique=True)

    # 2. sites
    op.create_table(
        "sites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="active", nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sites_company_id"), "sites", ["company_id"], unique=False)

    # 3. profiles (linked to Supabase auth.users.id)
    op.create_table(
        "profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("employee_id", sa.String(length=64), nullable=True),
        sa.Column("department", sa.String(length=120), nullable=True),
        sa.Column("job_title", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="active", nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_profiles_email"), "profiles", ["email"], unique=True)

    # 4. company_memberships
    op.create_table(
        "company_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=True),
        sa.Column("role", sa.String(length=48), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "company_id", name="uq_user_company_membership"),
    )
    op.create_index(op.f("ix_company_memberships_user_id"), "company_memberships", ["user_id"], unique=False)
    op.create_index(op.f("ix_company_memberships_company_id"), "company_memberships", ["company_id"], unique=False)


def downgrade() -> None:
    op.drop_table("company_memberships")
    op.drop_table("profiles")
    op.drop_table("sites")
    op.drop_table("companies")

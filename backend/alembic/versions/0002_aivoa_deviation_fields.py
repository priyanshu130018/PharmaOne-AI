"""add aivoa deviation fields: site_plant and ai recommendation audit columns

Revision ID: 0002_aivoa_deviation_fields
Revises: 0001_initial
Create Date: 2026-09-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_aivoa_deviation_fields"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _jsonb():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.add_column("deviations", sa.Column("site_plant", sa.String(length=160), nullable=True))
    op.add_column("deviations", sa.Column("ai_recommended_impact", sa.String(length=50), nullable=True))
    op.add_column("deviations", sa.Column("ai_recommended_severity", sa.String(length=50), nullable=True))
    op.add_column("deviations", sa.Column("ai_reason", sa.Text(), nullable=True))
    op.add_column("deviations", sa.Column("ai_evidence", _jsonb(), nullable=True))


def downgrade() -> None:
    op.drop_column("deviations", "ai_evidence")
    op.drop_column("deviations", "ai_reason")
    op.drop_column("deviations", "ai_recommended_severity")
    op.drop_column("deviations", "ai_recommended_impact")
    op.drop_column("deviations", "site_plant")

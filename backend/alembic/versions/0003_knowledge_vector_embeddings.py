"""add vector embedding and chunk_id to knowledge_chunks

Revision ID: 0003_knowledge_vector_embeddings
Revises: 0002_aivoa_deviation_fields
Create Date: 2026-09-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0003_knowledge_vector_embeddings"
down_revision: Union[str, None] = "0002_aivoa_deviation_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.add_column("knowledge_chunks", sa.Column("chunk_id", sa.String(length=128), nullable=True))
    op.create_index(op.f("ix_knowledge_chunks_chunk_id"), "knowledge_chunks", ["chunk_id"], unique=False)

    if bind.dialect.name == "postgresql":
        op.add_column("knowledge_chunks", sa.Column("embedding", Vector(384), nullable=True))
    else:
        op.add_column("knowledge_chunks", sa.Column("embedding", sa.JSON(), nullable=True))

    op.create_index(op.f("ix_knowledge_documents_checksum"), "knowledge_documents", ["checksum"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_knowledge_documents_checksum"), table_name="knowledge_documents")
    op.drop_column("knowledge_chunks", "embedding")
    op.drop_index(op.f("ix_knowledge_chunks_chunk_id"), table_name="knowledge_chunks")
    op.drop_column("knowledge_chunks", "chunk_id")

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, new_uuid

JSONVariant = JSON().with_variant(JSONB(), "postgresql")
VectorVariant = Vector(384).with_variant(JSON(), "sqlite")


class KnowledgeDocument(Base, TimestampMixin):
    """Metadata for a source document (e.g. an SOP or guideline) stored in Supabase Storage."""

    __tablename__ = "knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source: Mapped[str | None] = mapped_column(String(512), nullable=True)
    doc_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="registered")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    meta: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class KnowledgeChunk(Base, TimestampMixin):
    """Chunk of a knowledge document with dense embedding vector for similarity retrieval."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(VectorVariant, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")

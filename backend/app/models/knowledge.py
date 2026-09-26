import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, new_uuid

JSONVariant = JSON().with_variant(JSONB(), "postgresql")


class KnowledgeDocument(Base, TimestampMixin):
    """Metadata for a source document (e.g. an SOP or guideline) that the AI
    Deviation Assistant may reference. Only metadata is stored here; embeddings
    / vector storage are intentionally out of scope for this foundation."""

    __tablename__ = "knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source: Mapped[str | None] = mapped_column(String(512), nullable=True)
    doc_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="registered")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    meta: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class KnowledgeChunk(Base, TimestampMixin):
    """Metadata for an individual chunk of a knowledge document."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")

"""Unit and integration tests for Supabase Storage, RAG ingestion, and vector retrieval.

Verifies:
- Storage document retrieval and upload
- PDF text extraction and chunking
- Dense vector embedding generation (384-dim)
- knowledge_documents and knowledge_chunks database persistence
- Idempotency and SHA-256 checksum validation
- Query embedding and vector similarity retrieval
- Empty / invalid document error handling
- Storage failure handling
- Embedding API error fallback
- Verification against live Supabase Storage and PostgreSQL pgvector
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pypdf
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentExtractionError, StorageOperationError
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.services.ingestion_service import IngestionService, chunk_text
from app.services.rag_service import EMBEDDING_DIM, RagService
from app.services.storage_service import StorageService


def test_chunk_text_generation() -> None:
    """Verifies chunk_text correctly splits text into structured chunks with metadata."""
    sample_pages = [
        (1, "Quality Management System. Section 1.1 Scope and application of standard operating procedures."),
        (2, "Section 2.1 Environmental limits for Grade A cleanrooms. " * 30),  # Long page
    ]
    chunks = chunk_text(
        pages=sample_pages,
        doc_code="TEST-SOP",
        doc_title="Test SOP for Cleanrooms",
        filename="test_sop.pdf",
        target_words=50,
        overlap_words=10,
    )
    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk["chunk_id"].startswith("TEST-SOP-")
        assert chunk["content"]
        assert chunk["meta"]["document_name"] == "Test SOP for Cleanrooms"
        assert chunk["meta"]["filename"] == "test_sop.pdf"
        assert "page" in chunk["meta"]


def test_embedding_generation_dimension_and_normalization() -> None:
    """Verifies embeddings have 384 dimensions and unit Euclidean norm."""
    rag = RagService.get_instance()
    sample_query = "Autoclave temperature dropped below 121C during sterilization"
    vec = rag.embed_text(sample_query)
    assert len(vec) == EMBEDDING_DIM
    norm = sum(x * x for x in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-4

    vecs = rag.embed_texts([sample_query, "Cleanroom particle excursion"])
    assert len(vecs) == 2
    assert len(vecs[0]) == EMBEDDING_DIM
    assert len(vecs[1]) == EMBEDDING_DIM


def test_embedding_api_failure_fallback() -> None:
    """Verifies deterministic fallback embedding when Hugging Face API errors or is unreachable."""
    rag = RagService()
    with patch.object(rag, "_embed_huggingface", return_value=None):
        vec = rag.embed_text("Emergency line shutdown due to differential pressure failure")
        assert len(vec) == EMBEDDING_DIM
        norm = sum(x * x for x in vec) ** 0.5
        assert abs(norm - 1.0) < 1e-4


def test_storage_service_empty_upload_fails() -> None:
    """Uploading empty bytes must raise StorageOperationError."""
    storage = StorageService(supabase_url="https://fake.supabase.co", service_role_key="fake-key", client=MagicMock())
    with pytest.raises(StorageOperationError, match="Cannot upload empty file"):
        storage.upload_file("knowledge-base", "ref/empty.pdf", b"")


def test_storage_service_failure_handling() -> None:
    """Storage client exceptions are cleanly translated to StorageOperationError."""
    mock_client = MagicMock()
    mock_client.storage.from_().download.side_effect = Exception("Connection timed out to storage service")
    storage = StorageService(client=mock_client)

    with pytest.raises(StorageOperationError, match="Failed to download"):
        storage.download_file("knowledge-base", "missing.pdf")


@pytest.mark.asyncio
async def test_knowledge_persistence_and_checksum(db_session: AsyncSession) -> None:
    """Verifies persisting KnowledgeDocument and KnowledgeChunk with checksum validation."""
    content_bytes = b"PDF-CONTENT-EXAMPLE-12345"
    checksum = hashlib.sha256(content_bytes).hexdigest()

    doc = KnowledgeDocument(
        title="SOP-QA-099: Calibration Procedures",
        filename="SOP-QA-099.pdf",
        source="supabase://knowledge-base/reference-documents/SOP-QA-099.pdf",
        doc_type="SOP",
        checksum=checksum,
        status="indexed",
        chunk_count=2,
    )
    db_session.add(doc)
    await db_session.flush()

    chunk1 = KnowledgeChunk(
        document_id=doc.id,
        chunk_index=1,
        chunk_id="SOP-QA-099-C1",
        content="Section 1: Calibration tolerances for RTD temperature sensors.",
        embedding=[0.05] * 384,
        meta={"section": "Section 1", "page": 1},
    )
    chunk2 = KnowledgeChunk(
        document_id=doc.id,
        chunk_index=2,
        chunk_id="SOP-QA-099-C2",
        content="Section 2: Out of calibration escalation protocol.",
        embedding=[0.02] * 384,
        meta={"section": "Section 2", "page": 2},
    )
    db_session.add_all([chunk1, chunk2])
    await db_session.commit()

    # Query back
    stmt = select(KnowledgeDocument).where(KnowledgeDocument.checksum == checksum)
    res = await db_session.execute(stmt)
    retrieved_doc = res.scalars().first()
    assert retrieved_doc is not None
    assert retrieved_doc.chunk_count == 2

    chunks_stmt = select(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id)
    chunks_res = await db_session.execute(chunks_stmt)
    all_chunks = chunks_res.scalars().all()
    assert len(all_chunks) == 2
    assert all_chunks[0].chunk_id == "SOP-QA-099-C1"


@pytest.mark.asyncio
async def test_ingestion_idempotency(db_session: AsyncSession) -> None:
    """Verifies IngestionService skips already indexed documents with matching checksum."""
    pdf_bytes = b"%PDF-1.4 Mock document bytes"
    checksum = hashlib.sha256(pdf_bytes).hexdigest()

    # Pre-seed document
    doc = KnowledgeDocument(
        title="Form-450",
        filename="Form-450-Deviation-Report-Form.pdf",
        checksum=checksum,
        status="indexed",
        chunk_count=3,
    )
    db_session.add(doc)
    await db_session.commit()

    mock_storage = MagicMock()
    mock_storage.file_exists.return_value = True
    mock_storage.download_file.return_value = pdf_bytes

    ingestion = IngestionService(storage_service=mock_storage)
    result = await ingestion.ingest_document(
        session=db_session,
        filename="Form-450-Deviation-Report-Form.pdf",
        title="Form-450",
        doc_type="Report Form",
        doc_code="FORM-450",
    )
    assert result["status"] == "skipped"
    assert result["reason"] == "already_indexed"


@pytest.mark.asyncio
async def test_empty_or_corrupt_pdf_ingestion_fails(db_session: AsyncSession) -> None:
    """Ingesting an invalid or empty PDF raises DocumentExtractionError."""
    mock_storage = MagicMock()
    mock_storage.file_exists.return_value = True
    mock_storage.download_file.return_value = b"Not a real PDF stream"

    ingestion = IngestionService(storage_service=mock_storage)
    with pytest.raises(DocumentExtractionError):
        await ingestion.ingest_document(
            session=db_session,
            filename="corrupt.pdf",
            title="Corrupt PDF",
            doc_type="Test",
            doc_code="CORRUPT",
        )


@pytest.mark.asyncio
async def test_vector_similarity_retrieval() -> None:
    """Verifies RagService.retrieve returns relevant chunks with scores above threshold."""
    rag = RagService.get_instance()
    query = "Environmental monitoring sterile filling Grade A microbial limits"
    results, success, notes = rag.retrieve(query, top_k=3, min_similarity=0.20)

    assert success is True
    assert len(results) > 0
    for chunk in results:
        assert "document_name" in chunk
        assert "chunk_id" in chunk
        assert "similarity_score" in chunk
        assert chunk["similarity_score"] >= 0.20
        assert len(chunk["content"]) > 10


@pytest.mark.asyncio
async def test_rag_asearch_fallback_on_empty_db() -> None:
    """Verifies asearch safely falls back to in-memory index when database has no matches."""
    rag = RagService.get_instance()
    query = "Differential pressure failure in cleanroom suite"
    results, success, notes = await rag.asearch(query, session=None, top_k=2)

    assert success is True
    assert len(results) > 0
    assert "SOP" in results[0]["document_name"] or "Cleanroom" in results[0]["document_name"] or "ICH" in results[0]["document_name"]


@pytest.mark.asyncio
async def test_live_supabase_storage_and_vector_query() -> None:
    """Verifies live Supabase Storage bucket and live PostgreSQL pgvector chunks if live credentials exist."""
    import pathlib
    from dotenv import dotenv_values

    env_path = pathlib.Path(".env")
    if not env_path.exists():
        env_path = pathlib.Path(__file__).resolve().parents[2] / ".env"

    if not env_path.exists():
        pytest.skip("No .env file found; skipping live cloud verification.")

    real_env = dotenv_values(str(env_path))
    url = real_env.get("SUPABASE_URL")
    key = real_env.get("SUPABASE_SERVICE_ROLE_KEY")
    db_url = real_env.get("DATABASE_URL")

    if not url or "REPLACE" in url or not key or "REPLACE" in key or not db_url or "REPLACE" in db_url:
        pytest.skip("Live Supabase credentials not provided in .env; skipping live cloud verification.")

    from supabase import create_client
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    # 1. Verify Storage
    sb = create_client(url, key)
    buckets = sb.storage.list_buckets()
    bucket_names = [b.name for b in buckets]
    assert "knowledge-base" in bucket_names

    files = sb.storage.from_("knowledge-base").list("reference-documents")
    file_names = [f.get("name") if isinstance(f, dict) else getattr(f, "name", "") for f in files]
    assert "Form-450-Deviation-Report-Form.pdf" in file_names
    assert "ICH_Q9(R1)_Guideline_Step4_2025_0115_0.pdf" in file_names
    assert "using-cgmps-documents.pdf" in file_names

    # 2. Verify Database pgvector
    async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://") if "postgresql://" in db_url else db_url
    engine = create_async_engine(async_db_url)
    sessionmaker = async_sessionmaker(engine)

    rag = RagService.get_instance()
    query = "ICH Q9 risk assessment CQAs and sterile manufacturing parameters"
    vec = rag.embed_text(query)

    async with sessionmaker() as session:
        # Check documents
        docs_res = await session.execute(select(KnowledgeDocument))
        docs = docs_res.scalars().all()
        assert len(docs) >= 3

        # Check chunks
        chunks_res = await session.execute(select(KnowledgeChunk))
        chunks = chunks_res.scalars().all()
        assert len(chunks) >= 100

        # Vector similarity search against live pgvector
        stmt = (
            select(
                KnowledgeChunk.chunk_id,
                KnowledgeChunk.content,
                KnowledgeDocument.title,
                (1 - KnowledgeChunk.embedding.cosine_distance(vec)).label("similarity"),
            )
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .order_by(KnowledgeChunk.embedding.cosine_distance(vec))
            .limit(3)
        )
        res = await session.execute(stmt)
        top_chunks = res.all()
        assert len(top_chunks) == 3
        assert float(top_chunks[0].similarity) > 0.15

    await engine.dispose()

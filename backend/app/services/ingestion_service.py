"""RAG Knowledge Ingestion Service.

Implements the end-to-end knowledge ingestion pipeline:
1. Fetch/download reference PDF from private Supabase Storage (`knowledge-base/reference-documents/<filename>`)
2. Calculate document SHA-256 checksum for idempotency
3. If checksum matches and document is already indexed, skip duplicate ingestion
4. Extract text from PDF using pypdf
5. Split text into clean, semantic chunks with rich metadata (document name, page, section)
6. Generate dense embeddings once (sentence-transformers/all-MiniLM-L6-v2)
7. Persist document metadata in `knowledge_documents` and chunks + vectors in `knowledge_chunks`
"""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path
from typing import Any

import pypdf
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentExtractionError, StorageOperationError
from app.core.logging import get_logger
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.services.rag_service import RagService
from app.services.storage_service import (
    DEFAULT_KNOWLEDGE_BUCKET,
    REFERENCE_DOCS_PREFIX,
    StorageService,
)

logger = get_logger("pharmaone.ingestion")

# Standard operational reference documents
INITIAL_RAG_DOCUMENTS = [
    {
        "filename": "Form-450-Deviation-Report-Form.pdf",
        "title": "Form-450: Deviation Report Form Standard (Ref. SOP QMS-035 / MAN-080)",
        "doc_type": "Form / Report Standard",
        "doc_code": "FORM-450",
    },
    {
        "filename": "ICH_Q9(R1)_Guideline_Step4_2025_0115_0.pdf",
        "title": "ICH Q9(R1): Quality Risk Management Guideline (Step 4)",
        "doc_type": "Regulatory Guideline",
        "doc_code": "ICH-Q9-R1",
    },
    {
        "filename": "using-cgmps-documents.pdf",
        "title": "Using cGMPs in Manufacturing and Quality Operations",
        "doc_type": "cGMP Standard / SOP",
        "doc_code": "CGMP-DOC",
    },
]


def chunk_text(
    pages: list[tuple[int, str]],
    doc_code: str,
    doc_title: str,
    filename: str,
    target_words: int = 180,
    overlap_words: int = 30,
) -> list[dict[str, Any]]:
    """Split extracted PDF pages into clean semantic chunks with metadata."""
    chunks: list[dict[str, Any]] = []
    chunk_counter = 1

    for page_num, raw_page_text in pages:
        cleaned_text = re.sub(r"\s+", " ", raw_page_text).strip()
        if not cleaned_text:
            continue

        words = cleaned_text.split()
        if len(words) <= target_words:
            chunk_id = f"{doc_code}-P{page_num}-C{chunk_counter}"
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_counter,
                    "content": cleaned_text,
                    "meta": {
                        "document_name": doc_title,
                        "filename": filename,
                        "page": page_num,
                        "chunk_id": chunk_id,
                        "section": f"Page {page_num}",
                    },
                }
            )
            chunk_counter += 1
        else:
            idx = 0
            while idx < len(words):
                chunk_slice = words[idx : idx + target_words]
                chunk_str = " ".join(chunk_slice).strip()
                if chunk_str:
                    chunk_id = f"{doc_code}-P{page_num}-C{chunk_counter}"
                    chunks.append(
                        {
                            "chunk_id": chunk_id,
                            "chunk_index": chunk_counter,
                            "content": chunk_str,
                            "meta": {
                                "document_name": doc_title,
                                "filename": filename,
                                "page": page_num,
                                "chunk_id": chunk_id,
                                "section": f"Page {page_num} (Part {idx // max(1, target_words - overlap_words) + 1})",
                            },
                        }
                    )
                    chunk_counter += 1
                idx += target_words - overlap_words

    return chunks


class IngestionService:
    """Orchestrates PDF ingestion from Supabase Storage into PostgreSQL knowledge tables."""

    def __init__(
        self,
        storage_service: StorageService | None = None,
        rag_service: RagService | None = None,
    ) -> None:
        self.storage = storage_service or StorageService()
        self.rag = rag_service or RagService.get_instance()

    async def ingest_document(
        self,
        session: AsyncSession,
        filename: str,
        title: str,
        doc_type: str,
        doc_code: str,
        bucket_name: str = DEFAULT_KNOWLEDGE_BUCKET,
        force_reingest: bool = False,
        local_fallback_path: Path | None = None,
    ) -> dict[str, Any]:
        """Ingest a single document from Supabase Storage into the database."""
        storage_path = f"{REFERENCE_DOCS_PREFIX}/{filename}"

        # 1. Download PDF from Supabase Storage (upload from local if not yet in storage)
        pdf_bytes: bytes
        try:
            if not self.storage.file_exists(bucket_name, storage_path):
                if local_fallback_path and local_fallback_path.exists():
                    logger.info("Uploading local fallback file '%s' to Supabase Storage '%s'...", local_fallback_path, storage_path)
                    self.storage.upload_file(bucket_name, storage_path, local_fallback_path.read_bytes())
                else:
                    raise StorageOperationError(f"Document '{storage_path}' not found in Supabase bucket '{bucket_name}'.")
            pdf_bytes = self.storage.download_file(bucket_name, storage_path)
        except Exception as exc:
            logger.error("Failed to retrieve '%s' from Storage: %s", storage_path, exc)
            raise StorageOperationError(f"Failed to retrieve reference document '{filename}': {exc}") from exc

        # 2. Calculate checksum for idempotency
        checksum = hashlib.sha256(pdf_bytes).hexdigest()

        # 3. Check for existing document in knowledge_documents
        stmt = select(KnowledgeDocument).where(KnowledgeDocument.filename == filename)
        result = await session.execute(stmt)
        doc: KnowledgeDocument | None = result.scalars().first()

        if doc is not None and not force_reingest:
            if doc.checksum == checksum and doc.status == "indexed" and doc.chunk_count > 0:
                logger.info(
                    "Document '%s' already indexed with checksum %s (%d chunks). Skipping duplicate ingestion.",
                    filename,
                    checksum,
                    doc.chunk_count,
                )
                return {
                    "filename": filename,
                    "status": "skipped",
                    "reason": "already_indexed",
                    "checksum": checksum,
                    "chunk_count": doc.chunk_count,
                    "document_id": str(doc.id),
                }

        # 4. Extract text from PDF
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            if len(reader.pages) == 0:
                raise DocumentExtractionError(f"PDF document '{filename}' contains 0 pages.")
            pages_text: list[tuple[int, str]] = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages_text.append((i + 1, text))
        except Exception as exc:
            logger.error("Failed to parse PDF '%s': %s", filename, exc)
            raise DocumentExtractionError(f"Failed to parse reference PDF '{filename}': {exc}") from exc

        # 5. Split into semantic chunks
        chunks = chunk_text(pages_text, doc_code=doc_code, doc_title=title, filename=filename)
        if not chunks:
            raise DocumentExtractionError(f"No extractable text chunks could be generated for '{filename}'.")

        logger.info("Generated %d chunks for document '%s'", len(chunks), filename)

        # 6. Generate dense embeddings once
        chunk_texts_for_embed = [
            f"{c['meta']['document_name']} {c['meta']['section']}: {c['content']}"
            for c in chunks
        ]
        embeddings = self.rag.embed_texts(chunk_texts_for_embed)

        # 7. Persist to PostgreSQL knowledge tables
        if doc is None:
            doc = KnowledgeDocument(
                title=title,
                filename=filename,
                source=f"supabase://{bucket_name}/{storage_path}",
                doc_type=doc_type,
                checksum=checksum,
                status="indexing",
                chunk_count=len(chunks),
                meta={"doc_code": doc_code, "pages": len(pages_text)},
            )
            session.add(doc)
            await session.flush()
        else:
            # Reingestion: remove prior chunks
            await session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id))
            doc.title = title
            doc.doc_type = doc_type
            doc.checksum = checksum
            doc.chunk_count = len(chunks)
            doc.status = "indexing"
            await session.flush()

        for i, (chunk_data, emb) in enumerate(zip(chunks, embeddings)):
            chunk_rec = KnowledgeChunk(
                document_id=doc.id,
                chunk_index=chunk_data["chunk_index"],
                chunk_id=chunk_data["chunk_id"],
                content=chunk_data["content"],
                embedding=emb,
                meta=chunk_data["meta"],
            )
            session.add(chunk_rec)

        doc.status = "indexed"
        await session.commit()

        logger.info(
            "Successfully indexed '%s' (%d chunks, doc_id=%s, checksum=%s)",
            filename,
            len(chunks),
            doc.id,
            checksum,
        )

        return {
            "filename": filename,
            "status": "indexed",
            "checksum": checksum,
            "chunk_count": len(chunks),
            "document_id": str(doc.id),
        }

    async def ingest_all_initial_documents(
        self,
        session: AsyncSession,
        local_sources_dir: Path | None = None,
        force_reingest: bool = False,
    ) -> list[dict[str, Any]]:
        """Ingest all standard initial RAG reference documents."""
        results: list[dict[str, Any]] = []
        for doc_spec in INITIAL_RAG_DOCUMENTS:
            fname = doc_spec["filename"]
            local_path = (local_sources_dir / fname) if local_sources_dir else None
            res = await self.ingest_document(
                session=session,
                filename=fname,
                title=doc_spec["title"],
                doc_type=doc_spec["doc_type"],
                doc_code=doc_spec["doc_code"],
                force_reingest=force_reingest,
                local_fallback_path=local_path,
            )
            results.append(res)
        return results

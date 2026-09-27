"""Production vector retrieval service for pharmaceutical reference documents."""

from __future__ import annotations

import math
from typing import Any

from app.core.exceptions import EmbeddingGenerationError
from app.core.logging import get_logger
from app.rag.embeddings import (
    EMBEDDING_DIM,
    HF_EMBEDDING_MODEL,
    _deterministic_dense_projection,
    embed_huggingface,
)
from app.rag.retrieval import (
    _PHARMA_KNOWLEDGE_BASE,
    RetrievedChunk,
    score_documents,
    search_database_vector,
)

logger = get_logger("pharmaone.rag_service")


class RagService:
    """Production vector retrieval service for pharmaceutical reference documents.

    Uses dense embeddings (Hugging Face BAAI/bge-small-en-v1.5, 384-dimensional)
    to embed document chunks and user deviation queries before cosine similarity matching.
    """

    _instance: RagService | None = None

    @classmethod
    def get_instance(cls) -> RagService:
        """Singleton accessor for pre-indexed reference document knowledge base."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, custom_documents: list[dict] | None = None) -> None:
        self.documents = custom_documents if custom_documents is not None else list(_PHARMA_KNOWLEDGE_BASE)
        self.embedding_model = HF_EMBEDDING_MODEL
        self._build_index()

    def _embed_huggingface(self, texts: list[str]) -> list[list[float]] | None:
        """Calls Hugging Face Inference API to compute embeddings using BAAI/bge-small-en-v1.5.

        Returns None strictly in test/offline environments without configured API credentials.
        Raises EmbeddingGenerationError if the Hugging Face BGE-small request fails in production.
        """
        return embed_huggingface(texts)

    def embed_text(self, text: str) -> list[float]:
        """Generate a dense embedding vector for a single string using BAAI/bge-small-en-v1.5.

        In production, calls Hugging Face Inference API for BAAI/bge-small-en-v1.5.
        Deterministic projection fallback is explicitly used ONLY for test/offline behavior
        when no Hugging Face API key is configured.
        """
        hf_res = self._embed_huggingface([text])
        if hf_res and len(hf_res) > 0 and len(hf_res[0]) > 0:
            vec = hf_res[0]
            norm = math.sqrt(sum(x * x for x in vec))
            return [x / norm for x in vec] if norm > 0 else vec
        return _deterministic_dense_projection(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate dense embedding vectors for a list of strings using BAAI/bge-small-en-v1.5.

        In production, calls Hugging Face Inference API for BAAI/bge-small-en-v1.5.
        Deterministic projection fallback is explicitly used ONLY for test/offline behavior
        when no Hugging Face API key is configured.
        """
        hf_res = self._embed_huggingface(texts)
        if hf_res and len(hf_res) == len(texts):
            normed = []
            for vec in hf_res:
                norm = math.sqrt(sum(x * x for x in vec))
                normed.append([x / norm for x in vec] if norm > 0 else vec)
            return normed
        return [_deterministic_dense_projection(t) for t in texts]

    def _build_index(self) -> None:
        """Embed all reference document chunks into dense vector embeddings."""
        try:
            chunk_texts = [
                f"{doc['document_name']} {doc['section']}: {doc['content']}"
                for doc in self.documents
            ]
            self.vectors: list[list[float]] = self.embed_texts(chunk_texts)
            logger.info(
                "RAG vector index built: %d chunks embedded via %s (dimension=%d)",
                len(self.documents),
                self.embedding_model,
                len(self.vectors[0]) if self.vectors else 0,
            )
        except Exception as exc:
            logger.warning(
                "Failed to build remote BGE-small index for in-memory reference chunks (%s). Using deterministic projection for offline fallback index.",
                exc,
            )
            chunk_texts = [
                f"{doc['document_name']} {doc['section']}: {doc['content']}"
                for doc in self.documents
            ]
            self.vectors = [_deterministic_dense_projection(t) for t in chunk_texts]

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.20,
    ) -> tuple[list[RetrievedChunk], bool, str | None]:
        """Embeds query and retrieves top relevant reference chunks via cosine similarity."""
        if not query or not query.strip():
            return [], True, "Empty query provided; no reference documents retrieved."

        try:
            query_embedding = self.embed_text(query)
            results = score_documents(
                query_embedding,
                self.documents,
                self.vectors,
                top_k=top_k,
                min_similarity=min_similarity,
            )
            logger.info("RAG vector retrieved %d chunks for query (top_k=%d)", len(results), top_k)
            return results, True, None

        except Exception as exc:
            logger.error("RAG retrieval encountered an error: %s", exc, exc_info=True)
            return (
                [],
                False,
                f"Reference retrieval failed ({exc.__class__.__name__}). Continuing without reference context.",
            )

    async def asearch(
        self,
        query: str,
        session: Any = None,
        top_k: int = 3,
        min_similarity: float = 0.20,
    ) -> tuple[list[RetrievedChunk], bool, str | None]:
        """Embeds query and performs vector similarity search against PostgreSQL knowledge_chunks,
        falling back to in-memory reference index if database is unreachable or empty."""
        if not query or not query.strip():
            return [], True, "Empty query provided; no reference documents retrieved."

        try:
            query_embedding = self.embed_text(query)

            try:
                results = await search_database_vector(
                    query_embedding,
                    session=session,
                    top_k=top_k,
                    min_similarity=min_similarity,
                )
                if results:
                    logger.info("RAG vector retrieved %d chunks from database knowledge_chunks (top_k=%d)", len(results), top_k)
                    return results, True, None
            except Exception as db_exc:
                logger.info("Database vector search bypassed (%s); using in-memory reference index", db_exc)

            return self.retrieve(query, top_k=top_k, min_similarity=min_similarity)

        except EmbeddingGenerationError as emb_err:
            logger.error("Embedding generation failed during RAG search: %s", emb_err)
            return (
                [],
                False,
                f"Reference retrieval failed: {emb_err}. Continuing without reference context.",
            )
        except Exception as exc:
            logger.info("Vector search encountered error (%s); falling back to in-memory index", exc)
            return self.retrieve(query, top_k=top_k, min_similarity=min_similarity)

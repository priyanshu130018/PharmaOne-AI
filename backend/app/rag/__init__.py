"""RAG module for PharmaOne-AI reference retrieval."""

from app.rag.embeddings import (
    EMBEDDING_DIM,
    HF_EMBEDDING_MODEL,
    HF_ROUTER_URL,
    _cosine_similarity,
    _deterministic_dense_projection,
    embed_huggingface,
    embed_text,
    embed_texts,
)
from app.rag.retrieval import (
    _PHARMA_KNOWLEDGE_BASE,
    RetrievedChunk,
    score_documents,
    search_database_vector,
)
from app.rag.service import RagService

__all__ = [
    "RagService",
    "RetrievedChunk",
    "HF_EMBEDDING_MODEL",
    "HF_ROUTER_URL",
    "EMBEDDING_DIM",
    "_deterministic_dense_projection",
    "_cosine_similarity",
    "embed_huggingface",
    "embed_text",
    "embed_texts",
    "_PHARMA_KNOWLEDGE_BASE",
    "score_documents",
    "search_database_vector",
]

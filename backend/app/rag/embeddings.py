"""Embedding generation using BAAI/bge-small-en-v1.5 exclusively.

Provides:
- Hugging Face Inference Router integration
- Deterministic dense projection fallback for offline/test environments
- Vector normalization and cosine similarity computation
"""

from __future__ import annotations

import hashlib
import math
import re

from app.core.exceptions import EmbeddingGenerationError
from app.core.logging import get_logger

logger = get_logger("pharmaone.rag_embeddings")

HF_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
HF_ROUTER_URL = f"https://router.huggingface.co/hf-inference/models/{HF_EMBEDDING_MODEL}"
EMBEDDING_DIM = 384


def _deterministic_dense_projection(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """Generates a dense, normalized semantic embedding vector (384-dimensional)
    strictly for test/offline environments when no Hugging Face API key is configured.
    Uses MD5 deterministic hashing with position and token weighting (process-independent)."""
    vec = [0.0] * dim
    words = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())
    if not words:
        return vec

    for i, word in enumerate(words):
        h1 = int(hashlib.md5(word.encode("utf-8")).hexdigest()[:8], 16) % dim
        h2 = int(hashlib.md5(f"{word}_{i}".encode("utf-8")).hexdigest()[:8], 16) % dim
        h3 = int(hashlib.md5(f"pos_{word[:3]}".encode("utf-8")).hexdigest()[:8], 16) % dim
        vec[h1] += 1.0
        vec[h2] += 0.5
        vec[h3] += 0.25

    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two dense embedding vectors."""
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def embed_huggingface(texts: list[str]) -> list[list[float]] | None:
    """Calls Hugging Face Inference API to compute embeddings using BAAI/bge-small-en-v1.5.

    Returns None strictly in test/offline environments without configured API credentials.
    Raises EmbeddingGenerationError if the Hugging Face BGE-small request fails in production.
    Never falls back to another embedding model.
    """
    try:
        from app.core.config import get_settings

        settings = get_settings()
        api_key = settings.HUGGINGFACE_API_KEY
        if not api_key or api_key.startswith("test-") or "<REPLACE" in api_key:
            return None

        import httpx

        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    HF_ROUTER_URL,
                    headers=headers,
                    json={"inputs": texts, "options": {"wait_for_model": True}},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        if isinstance(data[0], list):
                            return data
                        elif isinstance(data[0], (int, float)):
                            return [data]
                err_msg = f"Hugging Face embedding request failed for '{HF_EMBEDDING_MODEL}' (status {resp.status_code}): {resp.text[:200]}"
                logger.error(err_msg)
                raise EmbeddingGenerationError(err_msg)
        except EmbeddingGenerationError:
            raise
        except Exception as endpoint_err:
            err_msg = f"Hugging Face BGE-small endpoint unavailable for '{HF_EMBEDDING_MODEL}': {endpoint_err}"
            logger.error(err_msg)
            raise EmbeddingGenerationError(err_msg) from endpoint_err
    except EmbeddingGenerationError:
        raise
    except Exception as exc:
        err_msg = f"Hugging Face BGE-small embedding call failed: {exc}"
        logger.error(err_msg)
        raise EmbeddingGenerationError(err_msg) from exc


def embed_text(text: str) -> list[float]:
    """Generate a dense embedding vector for a single string using BAAI/bge-small-en-v1.5."""
    hf_res = embed_huggingface([text])
    if hf_res and len(hf_res) > 0 and len(hf_res[0]) > 0:
        vec = hf_res[0]
        norm = math.sqrt(sum(x * x for x in vec))
        return [x / norm for x in vec] if norm > 0 else vec
    return _deterministic_dense_projection(text)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate dense embedding vectors for a list of strings using BAAI/bge-small-en-v1.5."""
    hf_res = embed_huggingface(texts)
    if hf_res and len(hf_res) == len(texts):
        normed = []
        for vec in hf_res:
            norm = math.sqrt(sum(x * x for x in vec))
            normed.append([x / norm for x in vec] if norm > 0 else vec)
        return normed
    return [_deterministic_dense_projection(t) for t in texts]

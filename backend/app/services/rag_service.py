"""Reference document retrieval and RAG service.

Implements vector-based retrieval over pharmaceutical reference documents
(SOPs, ICH guidelines, calibration procedures). Documents are chunked,
embedded, and indexed for similarity search.

Adheres strictly to the AIVOA workflow specification:
- RAG failure never crashes the application
- Retrieves only top relevant chunks (no full knowledge-base dumping)
- Preserves full source metadata (document name, section, similarity score)
"""

from __future__ import annotations

import math
import re
from typing import TypedDict

from app.core.logging import get_logger

logger = get_logger("pharmaone.rag")


class RetrievedChunk(TypedDict):
    document_name: str
    chunk_id: str
    section: str
    page_or_chunk: str
    similarity_score: float
    content: str


# ------------------------------------------------------------------------------
# Built-in Pharmaceutical Reference Knowledge Base
# ------------------------------------------------------------------------------

_PHARMA_KNOWLEDGE_BASE = [
    {
        "document_name": "SOP-QA-042: Environmental Monitoring & Cleanroom Control",
        "chunk_id": "SOP-QA-042-C1",
        "section": "Section 4.1 - Critical Particle and Microbial Action Limits",
        "page_or_chunk": "Page 3, Chunk 1",
        "content": (
            "Grade A filling areas: Maximum permitted particle limits are >= 0.5 um (3,520/m3) and "
            ">= 5.0 um (20/m3). Viable microbial count limit is < 1 CFU/m3. Any confirmed sterility or "
            "microbial growth excursion in Grade A/B immediately triggers line shutdown, product hold, "
            "and QA escalation. Containers filled during the excursion are quarantined pending investigation."
        ),
    },
    {
        "document_name": "SOP-QA-042: Environmental Monitoring & Cleanroom Control",
        "chunk_id": "SOP-QA-042-C2",
        "section": "Section 4.3 - Differential Pressure and HVAC Failure Modes",
        "page_or_chunk": "Page 5, Chunk 2",
        "content": (
            "Differential pressure between aseptic filling suite and adjacent corridor must maintain >= 15 Pa. "
            "If differential pressure drops below 10 Pa for more than 15 minutes, the room classification is "
            "compromised. Immediate action requires suspension of open-vial operations, air balance verification, "
            "and particulate monitoring before resumption."
        ),
    },
    {
        "document_name": "SOP-PR-108: Autoclave Operation & Sterilization Validation",
        "chunk_id": "SOP-PR-108-C1",
        "section": "Section 5.2 - Thermal Sterilization Parameters and Hold Criteria",
        "page_or_chunk": "Page 4, Chunk 1",
        "content": (
            "Standard moist-heat terminal sterilization cycle: Exposure at 121.1°C (+/- 0.5°C) for a minimum of "
            "20 minutes, achieving an F0 value >= 15 minutes. Temperature drop below 120.5°C during the sterilization "
            "exposure phase aborts the cycle and invalidates the sterility assurance level. The entire autoclave load "
            "must be quarantined."
        ),
    },
    {
        "document_name": "SOP-PR-108: Autoclave Operation & Sterilization Validation",
        "chunk_id": "SOP-PR-108-C2",
        "section": "Section 6.1 - Door Seal, Pressure Excursion, and Sensor Malfunctions",
        "page_or_chunk": "Page 7, Chunk 2",
        "content": (
            "Pressure loss or door gasket degradation during active autoclaving compromises sterilization envelope. "
            "Operators must lock out the unit, tag equipment 'Out of Service', notify maintenance, and quarantine all "
            "materials. Re-sterilization is permitted only if validated product heat-history limits are not exceeded."
        ),
    },
    {
        "document_name": "SOP-QC-215: Out of Specification (OOS) Laboratory Protocol",
        "chunk_id": "SOP-QC-215-C1",
        "section": "Section 3.2 - Phase I Laboratory Investigation Standards",
        "page_or_chunk": "Page 2, Chunk 1",
        "content": (
            "Phase I investigation must confirm analyst prep, instrument calibration (HPLC, GC, UV), system suitability, "
            "and reagent expiration before assigning lab error. Testing into compliance or averaging initial failing "
            "results with repeat testing is strictly prohibited under GMP guidelines."
        ),
    },
    {
        "document_name": "SOP-QC-215: Out of Specification (OOS) Laboratory Protocol",
        "chunk_id": "SOP-QC-215-C2",
        "section": "Section 4.4 - Phase II Manufacturing Investigation and Batch Disposition",
        "page_or_chunk": "Page 6, Chunk 2",
        "content": (
            "Phase II manufacturing investigation must assess raw materials, utility systems, batch formulation records, "
            "and environmental trends. Sterility test failures are non-retestable unless unequivocal laboratory sterility "
            "testing contamination is proven. Failing batches must be rejected."
        ),
    },
    {
        "document_name": "ICH-Q9: Quality Risk Management Guidance",
        "chunk_id": "ICH-Q9-C1",
        "section": "Section 5.1 - Quality Risk Assessment and Impact on Patient Safety",
        "page_or_chunk": "Page 8, Chunk 1",
        "content": (
            "Risk assessment consists of the identification of hazards and the analysis and evaluation of risks associated "
            "with exposure to those hazards. Critical risks directly impact Critical Quality Attributes (CQAs), product "
            "sterility, or patient safety. Major risks compromise validated limits without direct patient harm. Minor risks "
            "are isolated documentation or non-critical process variations."
        ),
    },
    {
        "document_name": "ICH-Q9: Quality Risk Management Guidance",
        "chunk_id": "ICH-Q9-C2",
        "section": "Section 5.3 - Decision Support and Human Review Governance",
        "page_or_chunk": "Page 11, Chunk 2",
        "content": (
            "Risk evaluations generated by algorithmic decision-support systems provide advisory risk classifications only. "
            "A qualified quality reviewer must confirm severity against approved company procedures, historical trend data, "
            "and cross-functional impact assessments before final approval."
        ),
    },
    {
        "document_name": "SOP-WH-031: Storage & Cold Chain Temperature Excursions",
        "chunk_id": "SOP-WH-031-C1",
        "section": "Section 3.1 - Cold Room (2°C to 8°C) Temperature Excursion Rules",
        "page_or_chunk": "Page 3, Chunk 1",
        "content": (
            "Refrigerated products must be maintained between 2.0°C and 8.0°C. Brief temperature excursions up to 12.0°C "
            "lasting less than 30 minutes require stability assessment. Any excursion above 15.0°C or lasting longer than "
            "2 hours requires immediate quarantine, notification of the QA head, and evaluation of mean kinetic temperature."
        ),
    },
    {
        "document_name": "SOP-EQ-104: Equipment Calibration & Sensor Drift Management",
        "chunk_id": "SOP-EQ-104-C1",
        "section": "Section 4.2 - Sensor Drift and Out-of-Tolerance Handling",
        "page_or_chunk": "Page 4, Chunk 1",
        "content": (
            "When a temperature, pressure, or pH sensor is found out of calibration tolerance, all batches manufactured "
            "since the last acceptable calibration check must be identified and subjected to a quality impact review. "
            "Critical sensor drifts invalidate process monitoring data."
        ),
    },
]


def _tokenize(text: str) -> list[str]:
    """Tokenize and normalize text for semantic vector matching."""
    return [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text)]


def _compute_vector(tokens: list[str], vocabulary: dict[str, int]) -> list[float]:
    """Compute normalized term-frequency vector."""
    vec = [0.0] * len(vocabulary)
    for tok in tokens:
        idx = vocabulary.get(tok)
        if idx is not None:
            vec[idx] += 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two unit vectors."""
    return sum(a * b for a, b in zip(vec1, vec2))


class RagService:
    """Production vector retrieval service for pharmaceutical reference documents.

    Maintains vector embeddings for knowledge chunks and performs cosine
    similarity retrieval. Fails safely without crashing if retrieval is unavailable.
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
        self._build_index()

    def _build_index(self) -> None:
        """Extract tokens, build shared vocabulary, and compute vector embeddings."""
        vocab: dict[str, int] = {}
        chunk_tokens: list[list[str]] = []

        for doc in self.documents:
            full_text = f"{doc['document_name']} {doc['section']} {doc['content']}"
            tokens = _tokenize(full_text)
            chunk_tokens.append(tokens)
            for t in tokens:
                if t not in vocab:
                    vocab[t] = len(vocab)

        self.vocabulary = vocab
        self.vectors: list[list[float]] = [
            _compute_vector(tokens, vocab) for tokens in chunk_tokens
        ]
        logger.debug(
            "RAG index built: %d chunks across vocabulary of %d terms",
            len(self.documents),
            len(self.vocabulary),
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.08,
    ) -> tuple[list[RetrievedChunk], bool, str | None]:
        """Retrieve top relevant chunks matching query.

        Returns:
            tuple[chunks, success, error_or_warning_message]
        """
        if not query or not query.strip():
            return [], True, "Empty query provided; no reference documents retrieved."

        try:
            query_tokens = _tokenize(query)
            if not query_tokens:
                return [], True, "Query contains no recognizable terms."

            query_vec = _compute_vector(query_tokens, self.vocabulary)
            # If query has zero overlap with vocabulary
            if not any(query_vec):
                return [], True, "No reference documents matched query vocabulary."

            scored: list[tuple[float, dict]] = []
            for doc, doc_vec in zip(self.documents, self.vectors):
                sim = _cosine_similarity(query_vec, doc_vec)
                if sim >= min_similarity:
                    scored.append((sim, doc))

            # Rank by similarity score descending
            scored.sort(key=lambda x: x[0], reverse=True)
            top_results = scored[:top_k]

            results: list[RetrievedChunk] = []
            for sim, doc in top_results:
                results.append(
                    {
                        "document_name": doc["document_name"],
                        "chunk_id": doc["chunk_id"],
                        "section": doc["section"],
                        "page_or_chunk": doc["page_or_chunk"],
                        "similarity_score": round(sim, 4),
                        "content": doc["content"],
                    }
                )

            logger.info("RAG retrieved %d chunks for query (top_k=%d)", len(results), top_k)
            return results, True, None

        except Exception as exc:
            logger.error("RAG retrieval encountered an error: %s", exc, exc_info=True)
            return (
                [],
                False,
                f"Reference retrieval failed ({exc.__class__.__name__}). Continuing without reference context.",
            )

"""Vector retrieval algorithms and built-in knowledge base for PharmaOne-AI."""

from __future__ import annotations

from typing import Any, TypedDict

from app.core.logging import get_logger
from app.rag.embeddings import _cosine_similarity

logger = get_logger("pharmaone.rag_retrieval")


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
        "document_name": "SOP-014 v3.2: Chemical Synthesis & Reactor Temperature Control",
        "chunk_id": "SOP-014-C1",
        "section": "Section 3.2 - Reaction Parameter Limits for Paracetamol API",
        "page_or_chunk": "Page 2, Chunk 1",
        "content": (
            "Approved temperature range is 76–80 °C for Step 3 (Reaction) of Paracetamol API synthesis. "
            "Any excursion above 80 °C (e.g. 84 °C) increases risk of degradation, formation of 4-aminophenol "
            "impurities, and acetic acid byproducts. Automatic cooling response must engage within 3 minutes. "
            "Valve actuator calibration and preventive maintenance controls must be strictly maintained."
        ),
    },
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


def score_documents(
    query_vec: list[float],
    documents: list[dict],
    vectors: list[list[float]],
    top_k: int = 3,
    min_similarity: float = 0.20,
) -> list[RetrievedChunk]:
    """Score document chunks against query vector using cosine similarity."""
    scored: list[tuple[float, dict]] = []
    for doc, doc_vec in zip(documents, vectors):
        sim = _cosine_similarity(query_vec, doc_vec)
        if sim >= min_similarity:
            scored.append((sim, doc))

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
    return results


async def search_database_vector(
    query_vec: list[float],
    session: Any = None,
    top_k: int = 3,
    min_similarity: float = 0.20,
) -> list[RetrievedChunk]:
    """Query PostgreSQL pgvector knowledge_chunks table using cosine distance."""
    from app.db.session import get_sessionmaker
    from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
    from sqlalchemy import select

    async def _run_db_query(s):
        cos_dist = KnowledgeChunk.embedding.cosine_distance(query_vec)
        max_dist = 1.0 - min_similarity
        stmt = (
            select(
                KnowledgeChunk.chunk_id,
                KnowledgeChunk.content,
                KnowledgeChunk.meta,
                KnowledgeDocument.title,
                (1.0 - cos_dist).label("similarity"),
            )
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(
                KnowledgeChunk.embedding.is_not(None),
                cos_dist <= max_dist,
            )
            .order_by(cos_dist)
            .limit(top_k)
        )
        res = await s.execute(stmt)
        return res.all()

    if session is not None:
        rows = await _run_db_query(session)
    else:
        sm = get_sessionmaker()
        async with sm() as s:
            rows = await _run_db_query(s)

    results: list[RetrievedChunk] = []
    if rows:
        for row in rows:
            sim = float(row.similarity) if row.similarity is not None else 0.0
            if sim >= min_similarity:
                meta = row.meta or {}
                results.append(
                    {
                        "document_name": row.title or meta.get("document_name", "Reference Document"),
                        "chunk_id": row.chunk_id or meta.get("chunk_id", ""),
                        "section": meta.get("section", "Standard Section"),
                        "page_or_chunk": f"Page {meta.get('page', 1)}" if meta.get("page") else meta.get("chunk_id", "Chunk"),
                        "similarity_score": round(sim, 4),
                        "content": row.content,
                    }
                )
    return results

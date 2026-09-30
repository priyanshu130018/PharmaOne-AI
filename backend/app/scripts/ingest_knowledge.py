"""CLI script to ingest reference documents into Supabase Storage and PostgreSQL knowledge tables.

Usage:
    # From project root:
    python -m backend.app.scripts.ingest_knowledge

    # From backend directory:
    python -m app.scripts.ingest_knowledge

    # With options:
    python -m app.scripts.ingest_knowledge --force
"""

from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys

# Ensure backend directory is on sys.path
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

for p in (str(BACKEND_DIR), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import dispose_engine, get_sessionmaker
from app.services.ingestion_service import IngestionService
from app.services.storage_service import DEFAULT_KNOWLEDGE_BUCKET, StorageService

logger = get_logger("pharmaone.scripts.ingest")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest RAG reference documents into Supabase Storage and DB")
    parser.add_argument("--force", action="store_true", help="Force re-ingestion of documents even if checksum matches")
    parser.add_argument("--bucket", default=DEFAULT_KNOWLEDGE_BUCKET, help="Supabase Storage bucket name")
    parser.add_argument(
        "--sources-dir",
        type=pathlib.Path,
        default=None,
        help="Local directory containing source PDFs for initial upload fallback",
    )
    args = parser.parse_args()

    configure_logging()
    settings = get_settings()
    logger.info("Initializing knowledge ingestion for environment: %s", settings.ENVIRONMENT)

    # Determine local sources directory
    sources_dir = args.sources_dir
    if sources_dir is None:
        candidate_dirs = [
            PROJECT_ROOT / "data" / "rag_sources",
            BACKEND_DIR / "data" / "rag_sources",
            PROJECT_ROOT / "docs",
        ]
        for c in candidate_dirs:
            if c.exists():
                sources_dir = c
                break

    logger.info("Local fallback sources directory: %s", sources_dir)

    storage_service = StorageService()
    storage_service.ensure_bucket(args.bucket)

    ingestion_service = IngestionService(storage_service=storage_service)
    sessionmaker = get_sessionmaker()

    async with sessionmaker() as session:
        results = await ingestion_service.ingest_all_initial_documents(
            session=session,
            local_sources_dir=sources_dir,
            force_reingest=args.force,
        )

    await dispose_engine()
    await asyncio.sleep(0.25)

    print("\n" + "=" * 80)
    print("PHARMAONE AI — KNOWLEDGE BASE INGESTION REPORT")
    print("=" * 80)
    print(f"{'Filename':<42} | {'Status':<8} | {'Chunks':<6} | {'Checksum':<16}")
    print("-" * 80)
    for r in results:
        fname = r.get("filename", "")
        status = r.get("status", "")
        chunks = r.get("chunk_count", 0)
        csum = (r.get("checksum") or "")[:14] + ".."
        print(f"{fname:<42} | {status:<8} | {chunks:<6} | {csum:<16}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

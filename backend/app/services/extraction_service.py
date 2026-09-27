"""Document and text extraction service.

Normalizes deviation text from:
1. Uploaded PDF documents (delegated to PdfService with OCR fallback).
2. Uploaded text documents (.txt, .log).
3. Pasted deviation text.
4. Pasted email content.

Enforces strict file type validation, size limits, and safe cleanup of temporary data.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.enums import DeviationSource
from app.core.exceptions import (
    DocumentExtractionError,
    EmptyPdfError,
    FileTooLargeError,
    UnsupportedFileTypeError,
    ValidationError,
)
from app.core.logging import get_logger
from app.schemas.extraction import (
    ExtractionMetadata,
    ExtractionResponse,
)
from app.services.ocr_service import OcrService
from app.services.pdf_service import PdfService

logger = get_logger("pharmaone.extraction")

_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".log"}
_EMAIL_HEADER_REGEX = re.compile(
    r"^(From|To|Subject|Date|Sent):\s+.+",
    re.IGNORECASE | re.MULTILINE,
)


class ExtractionService:
    """Coordinates text extraction from documents, files, and pasted content."""

    def __init__(
        self,
        ocr_service: OcrService | None = None,
        pdf_service: PdfService | None = None,
    ) -> None:
        self.ocr_service = ocr_service or OcrService()
        self.pdf_service = pdf_service or PdfService(ocr_service=self.ocr_service)
        self.settings = get_settings()

    # --------------------------------------------------------------------------
    # Text / Email Normalization
    # --------------------------------------------------------------------------

    def normalize_text(
        self,
        raw_text: str,
        declared_source: DeviationSource | None = None,
    ) -> ExtractionResponse:
        """Validate and normalize raw pasted text or email body."""
        if not raw_text or not raw_text.strip():
            raise ValidationError("Pasted text content cannot be empty or whitespace only.")

        cleaned = raw_text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if len(cleaned) < 5:
            raise ValidationError("Pasted content is too short (minimum 5 characters required).")

        # Automatically detect email structure if not explicitly declared
        source_type = declared_source or DeviationSource.TEXT
        if source_type == DeviationSource.TEXT and _EMAIL_HEADER_REGEX.search(cleaned):
            source_type = DeviationSource.EMAIL

        metadata = ExtractionMetadata(
            filename=None,
            page_count=1,
            character_count=len(cleaned),
            ocr_applied=False,
            ocr_available=self.ocr_service.is_available(),
        )

        return ExtractionResponse(
            success=True,
            source_type=source_type,
            extracted_text=cleaned,
            metadata=metadata,
            error=None,
        )

    # --------------------------------------------------------------------------
    # File Stream & Security Validation
    # --------------------------------------------------------------------------

    async def _read_file_safe(self, file: UploadFile) -> tuple[bytes, str]:
        """Read uploaded file into memory while strictly enforcing size limit.

        Never exposes temporary filesystem paths to the caller.
        """
        filename = Path(file.filename or "upload").name
        ext = Path(filename).suffix.lower()

        if ext not in _ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(
                f"Unsupported file type '{ext or 'unknown'}'. "
                f"Only PDF (.pdf) and text documents (.txt, .log) are supported."
            )

        max_bytes = self.settings.MAX_UPLOAD_SIZE_BYTES
        max_mb = max_bytes // (1024 * 1024)

        # Stream file in chunks to prevent unbounded memory allocation
        content_chunks: list[bytes] = []
        total_size = 0

        while True:
            chunk = await file.read(65536)  # 64 KB
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_bytes:
                raise FileTooLargeError(
                    f"Uploaded file exceeds the maximum allowed size of {max_mb} MB."
                )
            content_chunks.append(chunk)

        file_bytes = b"".join(content_chunks)
        if len(file_bytes) == 0:
            if ext == ".pdf":
                raise EmptyPdfError("Uploaded PDF file is empty (0 bytes).")
            raise ValidationError("Uploaded file is empty (0 bytes).")

        return file_bytes, filename

    # --------------------------------------------------------------------------
    # File Extraction Orchestrator
    # --------------------------------------------------------------------------

    async def extract_from_file(self, file: UploadFile) -> ExtractionResponse:
        """Extract text from an uploaded file (PDF or text)."""
        file_bytes, filename = await self._read_file_safe(file)
        ext = Path(filename).suffix.lower()

        # Ephemeral processing in a temporary file (guaranteed cleanup)
        temp_dir = tempfile.mkdtemp(prefix="pharmaone_upload_")
        temp_file_path = os.path.join(temp_dir, "document" + ext)
        try:
            with open(temp_file_path, "wb") as f:
                f.write(file_bytes)

            if ext == ".pdf":
                return self._extract_from_pdf(file_bytes, filename)
            else:
                return self._extract_from_plain_text(file_bytes, filename)

        finally:
            # Immediate cleanup of temporary data (Security requirement)
            try:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except OSError as cleanup_err:
                logger.warning("Failed to clean up temporary upload directory: %s", cleanup_err)

    # --------------------------------------------------------------------------
    # PDF Extraction & OCR Fallback
    # --------------------------------------------------------------------------

    def _extract_from_pdf(self, pdf_bytes: bytes, filename: str) -> ExtractionResponse:
        """Parse PDF text and fall back to OCR if scanned/image-only, delegating to PdfService."""
        return self.pdf_service.extract_from_pdf(pdf_bytes, filename)

    @staticmethod
    def _is_scanned_or_sparse(text: str, page_count: int) -> bool:
        """Determine if extracted text is insufficient, indicating a scanned PDF."""
        return PdfService.is_scanned_or_sparse(text, page_count)

    # --------------------------------------------------------------------------
    # Plain Text Extraction
    # --------------------------------------------------------------------------

    def _extract_from_plain_text(self, file_bytes: bytes, filename: str) -> ExtractionResponse:
        """Extract and normalize text from .txt or .log files."""
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1")
            except Exception as dec_err:
                raise DocumentExtractionError(
                    f"Failed to decode text file: {dec_err}"
                ) from dec_err

        cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not cleaned:
            raise ValidationError("Uploaded text file contains no text.")

        source = DeviationSource.EMAIL if _EMAIL_HEADER_REGEX.search(cleaned) else DeviationSource.TEXT

        return ExtractionResponse(
            success=True,
            source_type=source,
            extracted_text=cleaned,
            metadata=ExtractionMetadata(
                filename=filename,
                page_count=1,
                character_count=len(cleaned),
                ocr_applied=False,
                ocr_available=self.ocr_service.is_available(),
            ),
        )

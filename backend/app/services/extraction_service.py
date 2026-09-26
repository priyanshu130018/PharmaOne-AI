"""Document and text extraction service.

Normalizes deviation text from:
1. Uploaded PDF documents (including scanned PDFs with OCR fallback).
2. Uploaded text documents (.txt, .log).
3. Pasted deviation text.
4. Pasted email content.

Enforces strict file type validation, size limits, and safe cleanup of temporary data.
"""

from __future__ import annotations

import io
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
    InvalidPdfError,
    UnsupportedFileTypeError,
    ValidationError,
)
from app.core.logging import get_logger
from app.schemas.extraction import (
    ExtractionError,
    ExtractionMetadata,
    ExtractionResponse,
)
from app.services.ocr_service import OcrService

logger = get_logger("pharmaone.extraction")

_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".log"}
_EMAIL_HEADER_REGEX = re.compile(
    r"^(From|To|Subject|Date|Sent):\s+.+",
    re.IGNORECASE | re.MULTILINE,
)


class ExtractionService:
    """Coordinates text extraction from documents, files, and pasted content."""

    def __init__(self, ocr_service: OcrService | None = None) -> None:
        self.ocr_service = ocr_service or OcrService()
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
        """Parse PDF text with pypdf and fall back to OCR if scanned/image-only."""
        # 1. Magic byte verification
        if not pdf_bytes.startswith(b"%PDF-"):
            raise InvalidPdfError(
                "Invalid or corrupted PDF file: missing standard PDF header."
            )

        # 2. Parse document structure
        try:
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        except Exception as parse_err:
            logger.warning("PDF parsing failed: %s", parse_err)
            raise InvalidPdfError(
                "Invalid or corrupted PDF file. The document structure could not be parsed."
            ) from parse_err

        page_count = len(reader.pages)
        if page_count == 0:
            raise EmptyPdfError("PDF document is empty (contains 0 pages).")

        # 3. Extract native text
        extracted_pages: list[str] = []
        for idx, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    extracted_pages.append(page_text.strip())
            except Exception as page_err:
                logger.warning("Error reading PDF page %d: %s", idx + 1, page_err)

        combined_text = "\n\n".join(extracted_pages).strip()

        # 4. Detect whether text is useful or if this is a scanned/image PDF
        is_scanned = self._is_scanned_or_sparse(combined_text, page_count)

        if not is_scanned and combined_text:
            return ExtractionResponse(
                success=True,
                source_type=DeviationSource.PDF,
                extracted_text=combined_text,
                metadata=ExtractionMetadata(
                    filename=filename,
                    page_count=page_count,
                    character_count=len(combined_text),
                    ocr_applied=False,
                    ocr_available=self.ocr_service.is_available(),
                ),
            )

        # 5. Scanned / image PDF detected -> trigger safe OCR fallback
        logger.info(
            "PDF '%s' has minimal/no native text. Triggering OCR fallback...",
            filename,
        )
        ocr_text, ocr_success, ocr_error = self.ocr_service.extract_text_from_pdf_bytes(
            pdf_bytes,
            max_pages=page_count,
        )

        if ocr_success and ocr_text.strip():
            return ExtractionResponse(
                success=True,
                source_type=DeviationSource.PDF,
                extracted_text=ocr_text.strip(),
                metadata=ExtractionMetadata(
                    filename=filename,
                    page_count=page_count,
                    character_count=len(ocr_text.strip()),
                    ocr_applied=True,
                    ocr_available=True,
                    warnings=["Text was extracted via OCR from scanned document."],
                ),
            )

        # OCR unavailable or failed: return structured error (safe, no application crash)
        error_code = "OCR_UNAVAILABLE" if not self.ocr_service.is_available() else "OCR_FAILED"
        if not ocr_error:
            error_code = "EMPTY_DOCUMENT"
            ocr_error = "The PDF contains no legible text or recognized content."

        return ExtractionResponse(
            success=False,
            source_type=DeviationSource.PDF,
            extracted_text="",
            metadata=ExtractionMetadata(
                filename=filename,
                page_count=page_count,
                character_count=0,
                ocr_applied=True,
                ocr_available=self.ocr_service.is_available(),
            ),
            error=ExtractionError(
                code=error_code,
                message=ocr_error,
            ),
        )

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

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------

    @staticmethod
    def _is_scanned_or_sparse(text: str, page_count: int) -> bool:
        """Determine if extracted text is insufficient, indicating a scanned PDF."""
        if not text or len(text.strip()) == 0:
            return True
        # Less than 20 characters total or less than 10 characters per page is likely scanned
        if len(text.strip()) < 20 or (len(text.strip()) / max(page_count, 1)) < 10:
            return True
        # Check ratio of readable alphanumeric characters vs control/whitespace
        alphanumeric = sum(1 for c in text if c.isalnum())
        if len(text) > 0 and (alphanumeric / len(text)) < 0.25:
            return True
        return False

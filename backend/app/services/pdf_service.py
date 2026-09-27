"""PDF parsing and text extraction service.

Extracts text from PDF documents using pypdf for native text
and dispatches to OcrService for scanned/image-based documents.
"""

from __future__ import annotations

import io

from app.core.enums import DeviationSource
from app.core.exceptions import (
    EmptyPdfError,
    InvalidPdfError,
)
from app.core.logging import get_logger
from app.schemas.extraction import (
    ExtractionError,
    ExtractionMetadata,
    ExtractionResponse,
)
from app.services.ocr_service import OcrService

logger = get_logger("pharmaone.pdf")


class PdfService:
    """Service dedicated to parsing and extracting text from PDF documents."""

    def __init__(self, ocr_service: OcrService | None = None) -> None:
        self.ocr_service = ocr_service or OcrService()

    @staticmethod
    def is_scanned_or_sparse(text: str, page_count: int) -> bool:
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

    def extract_from_pdf(self, pdf_bytes: bytes, filename: str) -> ExtractionResponse:
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
        is_scanned = self.is_scanned_or_sparse(combined_text, page_count)

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

        # OCR unavailable or failed: return structured error
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

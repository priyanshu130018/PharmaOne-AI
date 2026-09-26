"""OCR fallback service for scanned and image-based PDFs.

Isolated safely in the service layer to prevent crashes when external OCR
binaries (Tesseract / Poppler) are missing or misconfigured.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("pharmaone.ocr")


class OcrService:
    """Encapsulates OCR engine operations with safe failure modes."""

    def __init__(
        self,
        *,
        tesseract_cmd: str | None = None,
        ocr_enabled: bool | None = None,
    ) -> None:
        settings = get_settings()
        self.ocr_enabled = (
            ocr_enabled if ocr_enabled is not None else settings.OCR_ENABLED
        )
        self.tesseract_cmd = tesseract_cmd or settings.TESSERACT_CMD

    def is_available(self) -> bool:
        """Check whether Tesseract is reachable and operational."""
        if not self.ocr_enabled:
            return False
        try:
            import pytesseract

            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            pytesseract.get_tesseract_version()
            return True
        except Exception as exc:
            logger.debug("Tesseract OCR is not available: %s", exc)
            return False

    def extract_text_from_pdf_bytes(
        self,
        pdf_bytes: bytes,
        *,
        max_pages: int = 10,
    ) -> tuple[str, bool, str | None]:
        """Attempt OCR extraction from raw PDF bytes.

        Returns:
            tuple[extracted_text, success, error_or_warning_message]
        """
        if not self.ocr_enabled:
            return (
                "",
                False,
                "OCR fallback is disabled by configuration.",
            )

        if not self.is_available():
            return (
                "",
                False,
                "The document appears to be a scanned image or contains no digital text, "
                "and the OCR engine (Tesseract) is not available on this server. "
                "Please paste the deviation text directly or upload a text-based PDF.",
            )

        try:
            import pytesseract
            from pdf2image import convert_from_bytes
            from pdf2image.exceptions import (
                PDFInfoNotInstalledError,
                PDFPageCountError,
                PDFSyntaxError,
            )

            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

            try:
                images = convert_from_bytes(
                    pdf_bytes,
                    first_page=1,
                    last_page=max_pages,
                )
            except (PDFInfoNotInstalledError, PDFPageCountError, PDFSyntaxError) as render_err:
                logger.warning("PDF page rendering failed during OCR: %s", render_err)
                return (
                    "",
                    False,
                    "Scanned document detected, but PDF rendering tools (poppler) are not available. "
                    "Please paste deviation text directly.",
                )

            if not images:
                return (
                    "",
                    False,
                    "Scanned document could not be rendered into images for OCR.",
                )

            page_texts: list[str] = []
            for page_idx, img in enumerate(images, start=1):
                try:
                    text = pytesseract.image_to_string(img)
                    cleaned = text.strip()
                    if cleaned:
                        page_texts.append(cleaned)
                except Exception as page_exc:
                    logger.warning("OCR failed on page %d: %s", page_idx, page_exc)

            full_text = "\n\n".join(page_texts).strip()
            if not full_text:
                return (
                    "",
                    False,
                    "Scanned document was processed with OCR, but no legible text was recognized. "
                    "Please ensure the scan is clear or paste the text directly.",
                )

            return full_text, True, None

        except Exception as exc:
            logger.error("OCR execution encountered an unexpected error: %s", exc, exc_info=True)
            return (
                "",
                False,
                f"OCR processing failed unexpectedly ({exc.__class__.__name__}). Please paste text directly.",
            )

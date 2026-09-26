"""Schemas for document text extraction and normalization.

Adheres strictly to the Normalized Extraction Response format required by the
AIVOA Deviation Intake pipeline.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.enums import DeviationSource


class ExtractionMetadata(BaseModel):
    """Metadata describing the extracted document or text source."""

    filename: str | None = Field(
        default=None,
        description="Original sanitized filename if uploaded from a file.",
    )
    page_count: int = Field(
        default=0,
        ge=0,
        description="Total pages processed in the document (0 for raw text).",
    )
    character_count: int = Field(
        default=0,
        ge=0,
        description="Total character count of the normalized extracted text.",
    )
    ocr_applied: bool = Field(
        default=False,
        description="True if OCR was executed to extract or supplement text.",
    )
    ocr_available: bool = Field(
        default=True,
        description="True if OCR engine (Tesseract) is available on the host.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings encountered during extraction.",
    )


class ExtractionError(BaseModel):
    """Structured error descriptor when text extraction cannot succeed."""

    code: str = Field(
        ...,
        description="Machine-readable error code (e.g. OCR_UNAVAILABLE, EMPTY_DOCUMENT).",
    )
    message: str = Field(
        ...,
        description="Human-readable explanation and recommended user action.",
    )


class ExtractionResponse(BaseModel):
    """Normalized response schema returned by extraction endpoints."""

    success: bool = Field(
        ...,
        description="Whether usable text was extracted successfully.",
    )
    source_type: DeviationSource = Field(
        ...,
        description="Origin source type: pdf, text, or email.",
    )
    extracted_text: str = Field(
        default="",
        description="Clean, normalized text ready for downstream AI workflow.",
    )
    metadata: ExtractionMetadata = Field(
        default_factory=ExtractionMetadata,
        description="Extraction metadata including page count and OCR status.",
    )
    error: ExtractionError | None = Field(
        default=None,
        description="Structured error information when success is false.",
    )


class TextExtractionRequest(BaseModel):
    """JSON payload for extracting/normalizing pasted text or email."""

    text: str = Field(
        ...,
        min_length=1,
        description="Raw deviation text, shift report, or email body.",
    )
    source_type: DeviationSource = Field(
        default=DeviationSource.TEXT,
        description="Declared source type (text or email).",
    )

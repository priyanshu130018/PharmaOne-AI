"""Tests for the Deviation Input and PDF/Text Extraction pipeline.

Covers all required validation scenarios:
- valid text (JSON & form-data)
- empty text
- valid PDF
- invalid PDF (missing header & corrupt syntax)
- scanned PDF with OCR fallback (success, unavailable, failure)
- extraction failure graceful handling
- unsupported file type
- oversized file
- malformed multipart request
"""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from pypdf import PdfWriter

from app.api.deps import get_ocr_service
from app.core.config import get_settings
from app.main import app
from app.services.ocr_service import OcrService


def _create_text_pdf(text: str = "Sterility test failure observed in Batch B-2026-042") -> bytes:
    """Generate a valid single-page PDF in memory containing embedded text."""
    # Standard PDF-1.4 stream with embedded text in standard Type 1 font
    text_escaped = text.replace("(", "\\(").replace(")", "\\)")
    stream_content = f"BT\n/F1 12 Tf\n50 700 Td\n({text_escaped}) Tj\nET\n".encode("utf-8")
    stream_length = len(stream_content)

    pdf_template = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length " + str(stream_length).encode("ascii") + b" >>\nstream\n"
        + stream_content
        + b"endstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000372 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n455\n%%EOF"
    )
    return pdf_template


def _create_blank_pdf() -> bytes:
    """Generate a valid PDF with one blank page (simulates a scanned image page without text)."""
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ------------------------------------------------------------------------------
# Text Input Tests
# ------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_valid_text_json(client: AsyncClient):
    """Pasting valid deviation text via JSON returns normalized text and metadata."""
    payload = {
        "text": "Temperature excursion observed in storage room 3. Recorded value: 26.5C.",
        "source_type": "text",
    }
    res = await client.post("/api/v1/deviations/extract-text", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["source_type"] == "text"
    assert "Temperature excursion" in data["extracted_text"]
    assert data["metadata"]["character_count"] > 20
    assert data["metadata"]["page_count"] == 1
    assert data["error"] is None


@pytest.mark.asyncio
async def test_extract_valid_text_form(client: AsyncClient):
    """Pasting text via form-data is accepted."""
    res = await client.post(
        "/api/v1/deviations/extract-text",
        data={"text": "Vial capping line motor jammed during batch B-99. 40 units rejected."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["source_type"] == "text"
    assert "Vial capping line" in data["extracted_text"]


@pytest.mark.asyncio
async def test_extract_valid_email_detection(client: AsyncClient):
    """Email headers in text automatically classify source_type as email."""
    email_text = (
        "From: qa-supervisor@pharma.com\n"
        "To: qa-team@pharma.com\n"
        "Subject: High endotoxin in Purified Water loop\n\n"
        "Routine testing flagged elevated endotoxin levels in loop 2."
    )
    res = await client.post(
        "/api/v1/deviations/extract-text",
        json={"text": email_text, "source_type": "text"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["source_type"] == "email"


@pytest.mark.asyncio
async def test_extract_empty_text_json(client: AsyncClient):
    """Empty or whitespace-only text via JSON is rejected with 422."""
    res = await client.post(
        "/api/v1/deviations/extract-text",
        json={"text": "    \n\t  "},
    )
    assert res.status_code == 422
    assert "empty" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_empty_text_form(client: AsyncClient):
    """Empty text via form-data is rejected with 422."""
    res = await client.post(
        "/api/v1/deviations/extract-text",
        data={"text": "   "},
    )
    assert res.status_code == 422
    assert "empty" in res.json()["detail"].lower()


# ------------------------------------------------------------------------------
# PDF Input Tests
# ------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_valid_pdf(client: AsyncClient):
    """Uploading a valid text PDF extracts digital text with metadata."""
    pdf_bytes = _create_text_pdf("Sterility test failure observed in Batch B-2026-042")
    files = {"file": ("deviation_report.pdf", pdf_bytes, "application/pdf")}

    res = await client.post("/api/v1/deviations/extract-text", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["source_type"] == "pdf"
    assert "Sterility test failure" in data["extracted_text"]
    assert data["metadata"]["filename"] == "deviation_report.pdf"
    assert data["metadata"]["page_count"] == 1
    assert data["metadata"]["ocr_applied"] is False
    assert data["error"] is None


@pytest.mark.asyncio
async def test_extract_invalid_pdf_missing_header(client: AsyncClient):
    """Uploading a non-PDF file with a .pdf extension is rejected with 422."""
    files = {"file": ("fake.pdf", b"This is plain text not starting with PDF magic bytes", "application/pdf")}
    res = await client.post("/api/v1/deviations/extract-text", files=files)
    assert res.status_code == 422
    assert "header" in res.json()["detail"].lower() or "invalid" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_invalid_pdf_corrupted_structure(client: AsyncClient):
    """Uploading a corrupted PDF stream is rejected cleanly with 422."""
    corrupt_bytes = b"%PDF-1.4\ncorrupted-content-with-broken-objects-and-no-trailer"
    files = {"file": ("corrupted.pdf", corrupt_bytes, "application/pdf")}
    res = await client.post("/api/v1/deviations/extract-text", files=files)
    assert res.status_code == 422
    assert "corrupt" in res.json()["detail"].lower() or "structure" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_empty_pdf_zero_bytes(client: AsyncClient):
    """Uploading a 0-byte PDF is rejected with 422."""
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    res = await client.post("/api/v1/deviations/extract-text", files=files)
    assert res.status_code == 422
    assert "empty" in res.json()["detail"].lower()


# ------------------------------------------------------------------------------
# Scanned PDF and OCR Fallback Tests
# ------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_scanned_pdf_ocr_success(client: AsyncClient):
    """Scanned PDF with no digital text triggers OCR and extracts text when OCR succeeds."""
    blank_pdf = _create_blank_pdf()
    files = {"file": ("scanned_deviation.pdf", blank_pdf, "application/pdf")}

    mock_ocr = MagicMock(spec=OcrService)
    mock_ocr.is_available.return_value = True
    mock_ocr.extract_text_from_pdf_bytes.return_value = (
        "OCR Extracted: Autoclave door seal degradation in Room 102",
        True,
        None,
    )

    app.dependency_overrides[get_ocr_service] = lambda: mock_ocr
    try:
        res = await client.post("/api/v1/deviations/extract-text", files=files)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["metadata"]["ocr_applied"] is True
        assert "Autoclave door seal degradation" in data["extracted_text"]
        assert data["error"] is None
    finally:
        app.dependency_overrides.pop(get_ocr_service, None)


@pytest.mark.asyncio
async def test_extract_scanned_pdf_ocr_unavailable(client: AsyncClient):
    """When OCR is unavailable, a scanned PDF safely returns structured error without crashing."""
    blank_pdf = _create_blank_pdf()
    files = {"file": ("scanned_no_ocr.pdf", blank_pdf, "application/pdf")}

    mock_ocr = MagicMock(spec=OcrService)
    mock_ocr.is_available.return_value = False
    mock_ocr.extract_text_from_pdf_bytes.return_value = (
        "",
        False,
        "Scanned document detected, but OCR engine is unavailable.",
    )

    app.dependency_overrides[get_ocr_service] = lambda: mock_ocr
    try:
        res = await client.post("/api/v1/deviations/extract-text", files=files)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is False
        assert data["metadata"]["ocr_applied"] is True
        assert data["metadata"]["ocr_available"] is False
        assert data["error"]["code"] == "OCR_UNAVAILABLE"
        assert "unavailable" in data["error"]["message"].lower()
    finally:
        app.dependency_overrides.pop(get_ocr_service, None)


@pytest.mark.asyncio
async def test_extract_scanned_pdf_ocr_failure(client: AsyncClient):
    """When OCR fails during execution, a structured error is returned safely without crashing."""
    blank_pdf = _create_blank_pdf()
    files = {"file": ("scanned_fail.pdf", blank_pdf, "application/pdf")}

    mock_ocr = MagicMock(spec=OcrService)
    mock_ocr.is_available.return_value = True
    mock_ocr.extract_text_from_pdf_bytes.return_value = (
        "",
        False,
        "OCR processing failed: unreadable image content.",
    )

    app.dependency_overrides[get_ocr_service] = lambda: mock_ocr
    try:
        res = await client.post("/api/v1/deviations/extract-text", files=files)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is False
        assert data["error"]["code"] == "OCR_FAILED"
        assert "unreadable" in data["error"]["message"].lower()
    finally:
        app.dependency_overrides.pop(get_ocr_service, None)


# ------------------------------------------------------------------------------
# Security, Size, and Format Validation Tests
# ------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_unsupported_file_type(client: AsyncClient):
    """Uploading executable or unsupported file extension is rejected with 415."""
    files = {"file": ("malware.exe", b"binarycontent", "application/octet-stream")}
    res = await client.post("/api/v1/deviations/extract-text", files=files)
    assert res.status_code == 415
    assert "unsupported" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_oversized_file(client: AsyncClient):
    """Files exceeding MAX_UPLOAD_SIZE_BYTES are rejected with 413."""
    settings = get_settings()
    # Mock settings.MAX_UPLOAD_SIZE_BYTES to 100 bytes for this test
    with patch.object(settings, "MAX_UPLOAD_SIZE_BYTES", 100):
        oversized_data = b"A" * 500
        files = {"file": ("large_report.txt", oversized_data, "text/plain")}
        res = await client.post("/api/v1/deviations/extract-text", files=files)
        assert res.status_code == 413
        assert "maximum allowed size" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_malformed_multipart_request(client: AsyncClient):
    """Multipart POST with neither file nor text is rejected with 400."""
    res = await client.post(
        "/api/v1/deviations/extract-text",
        data={},
    )
    assert res.status_code == 400
    assert "malformed" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_extract_plain_text_file(client: AsyncClient):
    """Uploading a .txt file is supported and properly extracted."""
    text_content = "Deviation Log 2026-09-26:\nDifferential pressure drop across HEPA filter in Cleanroom B."
    files = {"file": ("shift_report.txt", text_content.encode("utf-8"), "text/plain")}
    res = await client.post("/api/v1/deviations/extract-text", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["source_type"] == "text"
    assert "Differential pressure drop" in data["extracted_text"]
    assert data["metadata"]["filename"] == "shift_report.txt"

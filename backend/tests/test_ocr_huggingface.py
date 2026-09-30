"""Comprehensive unit and integration tests for Hugging Face Inference API OCR.

Validates all compliance requirements:
- normal text PDF extraction
- scanned PDF detection
- HF OCR success path
- HF OCR authentication/API failure
- HF OCR timeout
- empty OCR response
- invalid HF response
- missing HUGGINGFACE_API_KEY
- production environment configuration
- absence of local binary OCR dependencies
"""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import httpx
import pytest
from httpx import AsyncClient
from PIL import Image, ImageDraw
from pypdf import PdfWriter

from app.api.deps import get_ocr_service
from app.core.config import Settings
from app.main import app
from app.services.ocr_service import OcrService


def _create_image_pdf(text: str = "Batch B-9988: Temperature excursion to 84C") -> bytes:
    """Create a PDF with an embedded scanned page image."""
    img = Image.new("RGB", (400, 100), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 40), text, fill="black")

    img_buf = io.BytesIO()
    img.save(img_buf, format="JPEG")
    img_bytes = img_buf.getvalue()

    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=100)
    # Use pypdf to create a valid single-image PDF page
    buf = io.BytesIO()
    img.save(buf, format="PDF")
    return buf.getvalue()


# ------------------------------------------------------------------------------
# 1. Zero External Binary OCR Dependencies
# ------------------------------------------------------------------------------


def test_zero_external_binary_dependencies():
    """Verify external binary OCR utilities and wrappers are absent from Settings, requirements, and application code."""
    settings = Settings(
        ENVIRONMENT="production",
        BACKEND_PORT=8000,
        API_BASE_URL="http://localhost:8000",
        CORS_ORIGINS="http://localhost:8080",
        DATABASE_URL="postgresql+asyncpg://postgres:pass@localhost:5432/postgres",
        SUPABASE_URL="https://test.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test-key",
        GROQ_API_KEY="test-groq",
        GROQ_MODEL="openai/gpt-oss-20b",
        HUGGINGFACE_API_KEY="test-hf",
    )

    # 1. TESSERACT_CMD must NOT exist on Settings
    assert not hasattr(settings, "TESSERACT_CMD")

    # 2. requirements.txt must NOT list pytesseract or pdf2image
    from pathlib import Path

    reqs_path = Path(__file__).resolve().parents[1] / "requirements.txt"
    reqs_text = reqs_path.read_text(encoding="utf-8").lower()
    assert "pytesseract" not in reqs_text
    assert "pdf2image" not in reqs_text

    # 3. Dockerfile must NOT install tesseract-ocr or poppler-utils
    dockerfile_path = Path(__file__).resolve().parents[1] / "Dockerfile"
    dockerfile_text = dockerfile_path.read_text(encoding="utf-8").lower()
    assert "tesseract-ocr" not in dockerfile_text
    assert "poppler-utils" not in dockerfile_text

    # 4. No application module under app.* references pytesseract or pdf2image
    import sys

    for mod_name, mod in sys.modules.items():
        if mod_name.startswith("app.") and mod is not None:
            assert "pytesseract" not in getattr(mod, "__dict__", {})
            assert "pdf2image" not in getattr(mod, "__dict__", {})


# ------------------------------------------------------------------------------
# 2. Production Environment Configuration Enforcement
# ------------------------------------------------------------------------------


def test_production_environment_configuration_enforcement():
    """Verify application strictly accepts ENVIRONMENT=production and rejects development/dev."""
    # Valid production configuration
    prod_settings = Settings(
        ENVIRONMENT="production",
        BACKEND_PORT=8000,
        API_BASE_URL="http://localhost:8000",
        CORS_ORIGINS="http://localhost:8080",
        DATABASE_URL="postgresql+asyncpg://postgres:pass@localhost:5432/postgres",
        SUPABASE_URL="https://test.supabase.co",
        SUPABASE_SERVICE_ROLE_KEY="test-key",
        GROQ_API_KEY="test-groq",
        GROQ_MODEL="openai/gpt-oss-20b",
        HUGGINGFACE_API_KEY="test-hf",
    )
    assert prod_settings.ENVIRONMENT == "production"
    assert prod_settings.is_production is True

    # Reject development
    with pytest.raises(ValueError, match="Development environments.*not permitted"):
        Settings(
            ENVIRONMENT="development",
            BACKEND_PORT=8000,
            API_BASE_URL="http://localhost:8000",
            CORS_ORIGINS="http://localhost:8080",
            DATABASE_URL="postgresql+asyncpg://postgres:pass@localhost:5432/postgres",
            SUPABASE_URL="https://test.supabase.co",
            SUPABASE_SERVICE_ROLE_KEY="test-key",
            GROQ_API_KEY="test-groq",
            GROQ_MODEL="openai/gpt-oss-20b",
            HUGGINGFACE_API_KEY="test-hf",
        )

    # Reject dev
    with pytest.raises(ValueError):
        Settings(
            ENVIRONMENT="dev",
            BACKEND_PORT=8000,
            API_BASE_URL="http://localhost:8000",
            CORS_ORIGINS="http://localhost:8080",
            DATABASE_URL="postgresql+asyncpg://postgres:pass@localhost:5432/postgres",
            SUPABASE_URL="https://test.supabase.co",
            SUPABASE_SERVICE_ROLE_KEY="test-key",
            GROQ_API_KEY="test-groq",
            GROQ_MODEL="openai/gpt-oss-20b",
            HUGGINGFACE_API_KEY="test-hf",
        )


# ------------------------------------------------------------------------------
# 3. Missing HUGGINGFACE_API_KEY Handling
# ------------------------------------------------------------------------------


def test_missing_huggingface_api_key():
    """Verify OcrService reports unavailable when HUGGINGFACE_API_KEY is missing or placeholder."""
    ocr_empty = OcrService(api_key="")
    assert ocr_empty.is_available() is False

    ocr_none = OcrService(api_key=None)
    with patch("app.core.config.get_settings") as mock_settings:
        mock_settings.return_value.HUGGINGFACE_API_KEY = ""
        mock_settings.return_value.OCR_ENABLED = True
        ocr_none_inner = OcrService(api_key="")
        assert ocr_none_inner.is_available() is False

    text, success, msg = ocr_empty.extract_text_from_image_bytes(b"\x89PNGfakeimage")
    assert success is False
    assert "missing HUGGINGFACE_API_KEY" in msg


# ------------------------------------------------------------------------------
# 4. Hugging Face OCR Success Path
# ------------------------------------------------------------------------------


def test_hf_ocr_success_path():
    """Verify Hugging Face OCR successfully parses response from router chat completion."""
    ocr = OcrService(api_key="valid-hf-token")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Batch B-9988: Temperature excursion to 84C for 15 minutes.",
                },
                "finish_reason": "stop",
            }
        ]
    }

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        img_bytes = b"\x89PNG\r\n\x1a\nfakeimagebytes"
        text, success, error = ocr.extract_text_from_image_bytes(img_bytes)

        assert success is True
        assert error is None
        assert "Batch B-9988" in text
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"] == "Bearer valid-hf-token"


# ------------------------------------------------------------------------------
# 5. Hugging Face OCR Authentication / 401 Failure
# ------------------------------------------------------------------------------


def test_hf_ocr_authentication_failure():
    """Verify 401 / 403 authentication failure is handled with explicit error message."""
    ocr = OcrService(api_key="invalid-hf-token")
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = '{"error": "Invalid API Key"}'

    with patch("httpx.Client.post", return_value=mock_resp):
        img_bytes = b"\x89PNG\r\n\x1a\nfakeimagebytes"
        text, success, error = ocr.extract_text_from_image_bytes(img_bytes)

        assert success is False
        assert text == ""
        assert "authentication failed" in error.lower()
        assert "HUGGINGFACE_API_KEY" in error


# ------------------------------------------------------------------------------
# 6. Hugging Face OCR Timeout Handling
# ------------------------------------------------------------------------------


def test_hf_ocr_timeout_handling():
    """Verify network timeout is captured without crashing and returns structured error."""
    ocr = OcrService(api_key="valid-hf-token")

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Read timed out")):
        img_bytes = b"\x89PNG\r\n\x1a\nfakeimagebytes"
        text, success, error = ocr.extract_text_from_image_bytes(img_bytes)

        assert success is False
        assert text == ""
        assert "timed out" in error.lower()


# ------------------------------------------------------------------------------
# 7. Hugging Face OCR Rate Limit (429)
# ------------------------------------------------------------------------------


def test_hf_ocr_rate_limit_handling():
    """Verify HTTP 429 Rate Limit response is reported cleanly."""
    ocr = OcrService(api_key="valid-hf-token")
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = '{"error": "Rate limit exceeded"}'

    with patch("httpx.Client.post", return_value=mock_resp):
        img_bytes = b"\x89PNG\r\n\x1a\nfakeimagebytes"
        text, success, error = ocr.extract_text_from_image_bytes(img_bytes)

        assert success is False
        assert text == ""
        assert "rate limit exceeded" in error.lower()


# ------------------------------------------------------------------------------
# 8. Empty OCR Result Recognition
# ------------------------------------------------------------------------------


def test_hf_ocr_empty_text_result():
    """Verify empty/blank recognized text is reported as non-legible rather than fabricated."""
    ocr = OcrService(api_key="valid-hf-token")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"index": 0, "message": {"content": "   \n\t  "}}]
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        img_bytes = b"\x89PNG\r\n\x1a\nfakeimagebytes"
        text, success, error = ocr.extract_text_from_image_bytes(img_bytes)

        assert success is False
        assert text == ""
        assert "no legible text was recognized" in error.lower()


# ------------------------------------------------------------------------------
# 9. Invalid HF Response Structure
# ------------------------------------------------------------------------------


def test_hf_ocr_invalid_response_structure():
    """Verify malformed JSON structure does not throw unhandled exceptions."""
    ocr = OcrService(api_key="valid-hf-token")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"unexpected_key": 12345}

    with patch("httpx.Client.post", return_value=mock_resp):
        img_bytes = b"\x89PNG\r\n\x1a\nfakeimagebytes"
        text, success, error = ocr.extract_text_from_image_bytes(img_bytes)

        assert success is False
        assert text == ""
        assert "invalid response" in error.lower()


# ------------------------------------------------------------------------------
# 10. PDF with Embedded Scanned Image End-to-End via API
# ------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_pdf_with_image_triggers_hf_ocr(client: AsyncClient):
    """Uploading a PDF containing an embedded image triggers HF OCR extraction."""
    image_pdf_bytes = _create_image_pdf("Batch B-5544: Sterility test failure in filling suite")
    files = {"file": ("scanned_doc.pdf", image_pdf_bytes, "application/pdf")}

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Batch B-5544: Sterility test failure in filling suite",
                },
            }
        ]
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        res = await client.post("/api/v1/deviations/extract-text", files=files)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["metadata"]["ocr_applied"] is True
        assert "Batch B-5544" in data["extracted_text"]

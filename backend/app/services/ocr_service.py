"""Hugging Face Inference API OCR service for scanned and image-based PDFs.

Isolated safely in the service layer to process scanned/image documents
via Hugging Face vision models (e.g. Qwen/Qwen2.5-VL-72B-Instruct) without
requiring local OCR binaries or external system packages.
"""

from __future__ import annotations

import base64
import io

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("pharmaone.ocr")

HF_ROUTER_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
DEFAULT_OCR_MODEL = "Qwen/Qwen2.5-VL-72B-Instruct"
FALLBACK_OCR_MODEL = "Qwen/Qwen3-VL-30B-A3B-Instruct"


class OcrService:
    """Encapsulates Hugging Face Inference API OCR operations with safe failure modes."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        ocr_enabled: bool | None = None,
        timeout: float = 30.0,
    ) -> None:
        settings = get_settings()
        self.ocr_enabled = (
            ocr_enabled if ocr_enabled is not None else settings.OCR_ENABLED
        )
        self.api_key = api_key if api_key is not None else settings.HUGGINGFACE_API_KEY
        self.model = model or DEFAULT_OCR_MODEL
        self.timeout = timeout

    def is_available(self) -> bool:
        """Check whether Hugging Face OCR service is enabled and configured with an API key."""
        if not self.ocr_enabled:
            return False
        if not self.api_key or not self.api_key.strip():
            return False
        if "<REPLACE" in self.api_key:
            return False
        return True

    def extract_text_from_image_bytes(
        self,
        image_bytes: bytes,
    ) -> tuple[str, bool, str | None]:
        """Send an image to the Hugging Face Inference API for text recognition.

        Returns:
            tuple[extracted_text, success, error_or_warning_message]
        """
        if not self.ocr_enabled:
            return "", False, "OCR fallback is disabled by configuration."

        if not self.is_available():
            return (
                "",
                False,
                "The document appears to be a scanned image or contains no digital text, "
                "and Hugging Face OCR is not configured (missing HUGGINGFACE_API_KEY). "
                "Please paste the deviation text directly or upload a text-based PDF.",
            )

        if not image_bytes or len(image_bytes) == 0:
            return "", False, "Empty image bytes provided for OCR."

        # Detect image MIME type
        if image_bytes.startswith(b"\x89PNG"):
            mime_type = "image/png"
        elif image_bytes.startswith(b"\xff\xd8"):
            mime_type = "image/jpeg"
        elif image_bytes.startswith(b"GIF8"):
            mime_type = "image/gif"
        elif image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:16]:
            mime_type = "image/webp"
        else:
            mime_type = "image/png"

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64_image}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Try primary model, then fallback model if unavailable
        models_to_try = [self.model]
        if self.model != FALLBACK_OCR_MODEL:
            models_to_try.append(FALLBACK_OCR_MODEL)

        last_error = None
        for model_id in models_to_try:
            payload = {
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all text from this image exactly as written. Return only the extracted text.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            },
                        ],
                    }
                ],
                "max_tokens": 1500,
                "temperature": 0.0,
            }

            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        HF_ROUTER_CHAT_URL,
                        headers=headers,
                        json=payload,
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices") if isinstance(data, dict) else None
                    if choices and isinstance(choices, list) and len(choices) > 0:
                        content = choices[0].get("message", {}).get("content", "")
                        extracted = str(content).strip()
                        if extracted:
                            return extracted, True, None
                        return (
                            "",
                            False,
                            "Scanned document was processed with OCR, but no legible text was recognized.",
                        )
                    return "", False, "Hugging Face OCR returned an invalid response structure."

                if resp.status_code in (401, 403):
                    return (
                        "",
                        False,
                        "Hugging Face OCR authentication failed: invalid or unauthorized HUGGINGFACE_API_KEY.",
                    )

                if resp.status_code == 429:
                    return (
                        "",
                        False,
                        "Hugging Face OCR rate limit exceeded. Please try again later.",
                    )

                if resp.status_code == 503:
                    last_error = f"Hugging Face OCR model '{model_id}' is currently loading or unavailable."
                    continue

                # Other HTTP errors
                error_body = resp.text[:200]
                last_error = f"Hugging Face OCR request failed ({resp.status_code}): {error_body}"

            except httpx.TimeoutException:
                logger.warning("Hugging Face OCR request timed out for model %s", model_id)
                return "", False, "Hugging Face OCR request timed out."
            except httpx.ConnectError as conn_err:
                logger.warning("Hugging Face OCR connection error: %s", conn_err)
                return "", False, "Hugging Face OCR service is unreachable."
            except Exception as exc:
                logger.warning("Hugging Face OCR unexpected error with model %s: %s", model_id, exc)
                last_error = f"Hugging Face OCR processing failed unexpectedly: {exc}"

        return "", False, last_error or "Hugging Face OCR was unable to process the image."

    def extract_text_from_pdf_bytes(
        self,
        pdf_bytes: bytes,
        *,
        max_pages: int = 10,
    ) -> tuple[str, bool, str | None]:
        """Attempt OCR extraction from raw PDF bytes by extracting embedded images.

        Returns:
            tuple[extracted_text, success, error_or_warning_message]
        """
        if not self.ocr_enabled:
            return "", False, "OCR fallback is disabled by configuration."

        if not self.is_available():
            return (
                "",
                False,
                "The document appears to be a scanned image or contains no digital text, "
                "and Hugging Face OCR is not configured (missing HUGGINGFACE_API_KEY). "
                "Please paste the deviation text directly or upload a text-based PDF.",
            )

        try:
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        except Exception as parse_err:
            logger.warning("PDF parsing failed during OCR image extraction: %s", parse_err)
            return "", False, f"Could not parse PDF for OCR: {parse_err}"

        # Extract images from pages
        images_found: list[bytes] = []
        for page_idx, page in enumerate(reader.pages[:max_pages]):
            try:
                for img_obj in page.images:
                    if img_obj.data:
                        images_found.append(img_obj.data)
            except Exception as img_err:
                logger.warning("Error reading images from PDF page %d: %s", page_idx + 1, img_err)

        if not images_found:
            return (
                "",
                False,
                "Scanned document contains no recognized images or digital text for OCR.",
            )

        page_texts: list[str] = []
        for img_idx, img_bytes in enumerate(images_found, start=1):
            text, success, err = self.extract_text_from_image_bytes(img_bytes)
            if success and text:
                page_texts.append(text)
            elif err and not page_texts:
                # If the first image fails, fail fast with that specific error (e.g. auth, rate limit)
                return "", False, err

        if not page_texts:
            return (
                "",
                False,
                "Scanned document was processed with OCR, but no legible text was recognized.",
            )

        return "\n\n".join(page_texts).strip(), True, None

"""Pydantic schemas for the AI Deviation Intake Chat."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, model_validator


class DeviationChatRequest(BaseModel):
    """Payload for context-aware deviation intake chat."""

    message: str = Field(..., min_length=1, description="User question about deviation or form edit instruction")
    context: dict[str, Any] = Field(default_factory=dict, description="Extracted deviation fields")
    assessment: dict[str, Any] | None = Field(default=None, description="AI assessment result")
    current_form: dict[str, Any] = Field(default_factory=dict, description="Current user-edited form values")
    raw_content: str | None = Field(default=None, description="Original source text or OCR extracted text")


class FormFieldChange(BaseModel):
    """Structured representation of an applied form field change."""

    field: str = Field(..., description="Canonical or alias field identifier, e.g. 'site' or 'batch_number'")
    label: str = Field(..., description="Human-readable field label, e.g. 'Site / Plant'")
    old_value: Any = Field(default=None, description="Previous value before modification")
    new_value: Any = Field(default=None, description="New validated value")


class DeviationChatResponse(BaseModel):
    """Response returned by the context-aware deviation intake chat."""

    response: str = Field(default="", description="Assistant answer grounded in deviation context")
    intent: str = Field(default="answer_question", description="Structured action intent: 'update_form' or 'answer_question'")
    changes: list[FormFieldChange] = Field(default_factory=list, description="Structured list of validated applied form changes")
    message: str = Field(default="", description="Confirmation or answer message")

    @model_validator(mode="before")
    @classmethod
    def normalize_changes_before(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw_changes = data.get("changes")
            if isinstance(raw_changes, dict):
                # Convert dict mapping to list of FormFieldChange dicts for compatibility
                converted = []
                for k, v in raw_changes.items():
                    if isinstance(v, dict) and "new_value" in v:
                        converted.append(v)
                    else:
                        converted.append({
                            "field": k,
                            "label": str(k).replace("_", " ").title(),
                            "old_value": None,
                            "new_value": v,
                        })
                data["changes"] = converted
        return data

    @model_validator(mode="after")
    def sync_response_message(self) -> DeviationChatResponse:
        if not self.response and self.message:
            self.response = self.message
        elif not self.message and self.response:
            self.message = self.response
        return self


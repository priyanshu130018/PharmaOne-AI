import uuid
from datetime import date

from sqlalchemy import Date, Enum as SAEnum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.enums import (
    BatchStatus,
    DeviationSource,
    DeviationStatus,
    DeviationType,
    Impact,
    Severity,
)
from app.db.base import Base, TimestampMixin, new_uuid

# Use PostgreSQL JSONB in production but fall back to generic JSON on other
# backends (e.g. SQLite in tests). This keeps a single model portable.
JSONVariant = JSON().with_variant(JSONB(), "postgresql")


def _enum_col(enum_cls, length: int):
    return SAEnum(enum_cls, native_enum=False, length=length)


class Deviation(Base, TimestampMixin):
    """A logged manufacturing/quality deviation intake record.

    Field groups mirror the AIVOA "Log Deviation" form (Identification,
    Organization, Product, Event, Conditions, Immediate response, Assessment).
    Final saved values are the user's *reviewed* values; AI outputs are kept as
    snapshots in ``ai_extraction`` / ``ai_assessment`` for auditability.
    """

    __tablename__ = "deviations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)

    # --- Identification ---
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    source: Mapped[DeviationSource] = mapped_column(
        _enum_col(DeviationSource, 16), nullable=False, default=DeviationSource.MANUAL
    )
    reported_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    occurred_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    detected_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    # --- Organization ---
    # company_id/site_id are nullable UUIDs (no FK yet): the auth/org module is
    # a later step. They are here so the schema is ready without over-building.
    company_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    site_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    responsible_team: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # --- Product ---
    product_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    product_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    batch_number: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # --- Event ---
    manufacturing_stage: Mapped[str | None] = mapped_column(String(160), nullable=True)
    equipment: Mapped[str | None] = mapped_column(String(160), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    deviation_type: Mapped[DeviationType] = mapped_column(_enum_col(DeviationType, 32), nullable=False)

    # --- Conditions ---
    expected_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[str | None] = mapped_column(String(120), nullable=True)
    parameter: Mapped[str | None] = mapped_column(String(160), nullable=True)

    # --- Immediate response ---
    immediate_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    batch_status: Mapped[BatchStatus | None] = mapped_column(_enum_col(BatchStatus, 16), nullable=True)
    qa_notified: Mapped[bool | None] = mapped_column(nullable=True)

    # --- Assessment (final, user-reviewed) ---
    impact: Mapped[Impact | None] = mapped_column(_enum_col(Impact, 24), nullable=True)
    severity: Mapped[Severity | None] = mapped_column(_enum_col(Severity, 16), nullable=True)
    assessment_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[DeviationStatus] = mapped_column(
        _enum_col(DeviationStatus, 16), nullable=False, default=DeviationStatus.SUBMITTED
    )

    # --- AI snapshots (audit of what the assistant proposed) ---
    ai_extraction: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    ai_assessment: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Deviation {self.reference} status={self.status}>"

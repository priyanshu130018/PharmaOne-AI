import uuid

from sqlalchemy import Enum as SAEnum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.enums import AuditAction
from app.db.base import Base, TimestampMixin, new_uuid

JSONVariant = JSON().with_variant(JSONB(), "postgresql")


class AuditEvent(Base, TimestampMixin):
    """Immutable audit trail entry.

    In this foundation we record deviation-related actions. user_id/company_id
    are nullable and will be populated from the Supabase-authenticated identity
    once the auth module is implemented. Never store passwords or secrets here.
    """

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    action: Mapped[AuditAction] = mapped_column(
        SAEnum(AuditAction, native_enum=False, length=48), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(48), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    company_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    meta: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)

import uuid

from app.core.enums import AuditAction
from app.models.audit import AuditEvent
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditEvent]):
    model = AuditEvent

    async def record(
        self,
        *,
        action: AuditAction,
        entity_type: str,
        entity_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        company_id: uuid.UUID | None = None,
        meta: dict | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            company_id=company_id,
            meta=meta,
        )
        return await self.add(event)

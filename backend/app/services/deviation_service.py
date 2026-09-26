from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    AuditAction,
    DeviationStatus,
    DeviationType,
    Severity,
)
from app.core.exceptions import NotFoundError
from app.models.deviation import Deviation
from app.repositories.audit_repository import AuditRepository
from app.repositories.deviation_repository import DeviationRepository
from app.schemas.deviation import DeviationCreate, DeviationUpdate


class DeviationService:
    """Business logic for deviation intake. Owns orchestration and rules and
    records audit events; delegates all persistence to repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = DeviationRepository(session)
        self.audit = AuditRepository(session)

    async def create(self, payload: DeviationCreate) -> Deviation:
        reference = await self.repository.next_reference()
        data = payload.model_dump()

        if payload.ai_assessment and isinstance(payload.ai_assessment, dict):
            assessment = payload.ai_assessment
            if not data.get("ai_recommended_impact"):
                raw_imp = assessment.get("impact") or assessment.get("initial_impact")
                if raw_imp:
                    data["ai_recommended_impact"] = str(raw_imp.value if hasattr(raw_imp, "value") else raw_imp)
            if not data.get("ai_recommended_severity"):
                raw_sev = assessment.get("severity") or assessment.get("initial_severity")
                if raw_sev:
                    data["ai_recommended_severity"] = str(raw_sev.value if hasattr(raw_sev, "value") else raw_sev)
            if not data.get("ai_reason"):
                data["ai_reason"] = (
                    assessment.get("reason") or assessment.get("assessment_reason") or assessment.get("summary")
                )
            if not data.get("ai_evidence"):
                data["ai_evidence"] = (
                    assessment.get("evidence") or assessment.get("citations") or assessment.get("sop_citations")
                )

        deviation = Deviation(
            reference=reference,
            status=DeviationStatus.SUBMITTED,
            **data,
        )
        deviation = await self.repository.add(deviation)

        await self.audit.record(
            action=AuditAction.DEVIATION_CREATED,
            entity_type="deviation",
            entity_id=deviation.id,
            company_id=deviation.company_id,
            meta={"reference": deviation.reference, "had_ai": payload.ai_assessment is not None},
        )
        return deviation

    async def get(self, deviation_id: UUID) -> Deviation:
        deviation = await self.repository.get(deviation_id)
        if deviation is None:
            raise NotFoundError(f"Deviation {deviation_id} not found")
        return deviation

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        status: DeviationStatus | None = None,
        severity: Severity | None = None,
        deviation_type: DeviationType | None = None,
    ) -> tuple[list[Deviation], int]:
        return await self.repository.list(
            limit=limit,
            offset=offset,
            status=status,
            severity=severity,
            deviation_type=deviation_type,
        )

    async def update(self, deviation_id: UUID, payload: DeviationUpdate) -> Deviation:
        deviation = await self.get(deviation_id)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(deviation, field, value)
        await self.session.flush()
        await self.session.refresh(deviation)

        await self.audit.record(
            action=AuditAction.DEVIATION_UPDATED,
            entity_type="deviation",
            entity_id=deviation.id,
            company_id=deviation.company_id,
            meta={"fields": sorted(updates.keys())},
        )
        return deviation

    async def delete(self, deviation_id: UUID) -> None:
        deviation = await self.get(deviation_id)
        await self.repository.delete(deviation)

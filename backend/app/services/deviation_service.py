from uuid import UUID
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser
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
    """Business logic for deviation intake. Owns orchestration, rules,
    tenant data isolation, and records immutable audit events."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = DeviationRepository(session)
        self.audit = AuditRepository(session)

    async def create(self, payload: DeviationCreate, user: Optional[AuthenticatedUser] = None) -> Deviation:
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

        # Enforce tenancy from authenticated user context (never trusted from body)
        if user:
            data["company_id"] = user.company_id
            if user.site_id:
                data["site_id"] = user.site_id
            if not data.get("reported_by"):
                data["reported_by"] = user.full_name

        # Only pass columns that exist on the Deviation model
        valid_cols = {col.name for col in Deviation.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in valid_cols}

        deviation = Deviation(
            reference=reference,
            status=DeviationStatus.SUBMITTED,
            **filtered_data,
        )
        deviation = await self.repository.add(deviation)

        await self.audit.record(
            action=AuditAction.DEVIATION_CREATED,
            entity_type="deviation",
            entity_id=deviation.id,
            user_id=user.user_id if user else None,
            company_id=deviation.company_id,
            meta={"reference": deviation.reference, "had_ai": payload.ai_assessment is not None},
        )
        return deviation

    async def get(self, deviation_id: UUID, company_id: Optional[UUID] = None) -> Deviation:
        deviation = await self.repository.get(deviation_id)
        if deviation is None:
            raise NotFoundError(f"Deviation {deviation_id} not found")
        if company_id is not None and deviation.company_id != company_id:
            raise NotFoundError(f"Deviation {deviation_id} not found")
        return deviation

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        company_id: Optional[UUID] = None,
        status: DeviationStatus | None = None,
        severity: Severity | None = None,
        deviation_type: DeviationType | None = None,
    ) -> tuple[list[Deviation], int]:
        return await self.repository.list(
            limit=limit,
            offset=offset,
            company_id=company_id,
            status=status,
            severity=severity,
            deviation_type=deviation_type,
        )

    async def update(
        self,
        deviation_id: UUID,
        payload: DeviationUpdate,
        user: Optional[AuthenticatedUser] = None,
    ) -> Deviation:
        deviation = await self.get(deviation_id, company_id=user.company_id if user else None)
        updates = payload.model_dump(exclude_unset=True)
        # Prevent tenant hijacking
        updates.pop("company_id", None)
        for field, value in updates.items():
            setattr(deviation, field, value)
        await self.session.flush()
        await self.session.refresh(deviation)

        await self.audit.record(
            action=AuditAction.DEVIATION_UPDATED,
            entity_type="deviation",
            entity_id=deviation.id,
            user_id=user.user_id if user else None,
            company_id=deviation.company_id,
            meta={"updated_fields": list(updates.keys())},
        )
        return deviation

    async def delete(self, deviation_id: UUID, company_id: Optional[UUID] = None) -> None:
        deviation = await self.get(deviation_id, company_id=company_id)
        await self.repository.delete(deviation)

    async def summary(self, company_id: Optional[UUID] = None) -> dict:
        return await self.repository.summary(company_id=company_id)

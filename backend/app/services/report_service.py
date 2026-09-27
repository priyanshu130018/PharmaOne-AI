from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.deviation_repository import DeviationRepository
from app.schemas.report import CountByKey, DeviationReportSummary


class ReportService:
    """Read-only aggregates over persisted, user-reviewed deviations.

    Reports summarize saved final values scoped to tenant company.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.repository = DeviationRepository(session)

    async def summary(self, company_id: Optional[UUID] = None) -> DeviationReportSummary:
        data = await self.repository.summary(company_id=company_id)
        return DeviationReportSummary(
            total=data["total"],
            by_status=[CountByKey(key=k, count=c) for k, c in data["by_status"]],
            by_severity=[CountByKey(key=k, count=c) for k, c in data["by_severity"]],
            by_type=[CountByKey(key=k, count=c) for k, c in data["by_type"]],
        )

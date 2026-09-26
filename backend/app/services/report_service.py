from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.deviation_repository import DeviationRepository
from app.schemas.report import CountByKey, DeviationReportSummary


class ReportService:
    """Read-only aggregates over persisted, user-reviewed deviations.

    Reports summarize saved final values only — never unreviewed AI output.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.repository = DeviationRepository(session)

    async def summary(self) -> DeviationReportSummary:
        data = await self.repository.summary()
        return DeviationReportSummary(
            total=data["total"],
            by_status=[CountByKey(key=k, count=c) for k, c in data["by_status"]],
            by_severity=[CountByKey(key=k, count=c) for k, c in data["by_severity"]],
            by_type=[CountByKey(key=k, count=c) for k, c in data["by_type"]],
        )

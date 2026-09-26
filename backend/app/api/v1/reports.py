from fastapi import APIRouter

from app.api.deps import ReportServiceDep
from app.schemas.report import DeviationReportSummary

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/summary",
    response_model=DeviationReportSummary,
    summary="Aggregate summary of persisted deviations",
)
async def report_summary(service: ReportServiceDep) -> DeviationReportSummary:
    return await service.summary()

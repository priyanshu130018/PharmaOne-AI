from fastapi import APIRouter, Depends

from app.api.deps import ReportServiceDep
from app.core.auth import AuthenticatedUser, get_current_user
from app.schemas.report import DeviationReportSummary

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/summary",
    response_model=DeviationReportSummary,
    summary="Aggregate summary of persisted deviations",
)
async def report_summary(
    service: ReportServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DeviationReportSummary:
    """Retrieve deviation summary aggregates isolated to authenticated user's company."""
    return await service.summary(company_id=current_user.company_id)

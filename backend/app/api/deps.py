from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.deviation_service import DeviationService
from app.services.processing_service import ProcessingService
from app.services.report_service import ReportService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_deviation_service(session: SessionDep) -> DeviationService:
    return DeviationService(session)


def get_report_service(session: SessionDep) -> ReportService:
    return ReportService(session)


def get_processing_service() -> ProcessingService:
    return ProcessingService()


DeviationServiceDep = Annotated[DeviationService, Depends(get_deviation_service)]
ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
ProcessingServiceDep = Annotated[ProcessingService, Depends(get_processing_service)]

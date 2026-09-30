from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.deviation_service import DeviationService
from app.services.extraction_service import ExtractionService
from app.services.ocr_service import OcrService
from app.services.report_service import ReportService

from app.services.qms_service import QmsService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_deviation_service(session: SessionDep) -> DeviationService:
    return DeviationService(session)


def get_qms_service(session: SessionDep) -> QmsService:
    return QmsService(session)


def get_report_service(session: SessionDep) -> ReportService:
    return ReportService(session)


def get_ocr_service() -> OcrService:
    return OcrService()


def get_extraction_service(
    ocr_service: Annotated[OcrService, Depends(get_ocr_service)],
) -> ExtractionService:
    return ExtractionService(ocr_service=ocr_service)


DeviationServiceDep = Annotated[DeviationService, Depends(get_deviation_service)]
QmsServiceDep = Annotated[QmsService, Depends(get_qms_service)]
ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
ExtractionServiceDep = Annotated[ExtractionService, Depends(get_extraction_service)]

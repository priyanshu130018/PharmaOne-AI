from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status

from app.ai.chat import answer_deviation_chat
from app.ai.graph import process_deviation as run_ai_deviation_pipeline
from app.api.deps import (
    DeviationServiceDep,
    ExtractionServiceDep,
)
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.enums import DeviationSource, DeviationStatus, DeviationType, Severity
from app.core.exceptions import PharmaOneError, ValidationError
from app.schemas.chat import DeviationChatRequest, DeviationChatResponse
from app.schemas.deviation import (
    DeviationCreate,
    DeviationList,
    DeviationRead,
    DeviationUpdate,
)
from app.schemas.extraction import ExtractionResponse
from app.schemas.process import ProcessRequest, ProcessResponse
from app.schemas.qms import DeviationSeverityConfirm

router = APIRouter(prefix="/deviations", tags=["deviations"])


@router.post(
    "/extract-text",
    response_model=ExtractionResponse,
    summary="Extract normalized text from document upload or pasted text/email",
    description=(
        "Primary input endpoint for the AI Deviation Intake pipeline.\n\n"
        "Accepts either an uploaded PDF/text document or pasted text/email content.\n"
        "Performs normalization, automatic scanned-PDF detection, and safe OCR fallback."
    ),
)
async def extract_text(
    request: Request,
    service: ExtractionServiceDep,
    file: UploadFile | None = File(default=None, description="Deviation document (PDF, TXT, LOG)"),
    text: str | None = Form(default=None, description="Pasted deviation text or email body"),
    source_type: DeviationSource | None = Form(default=None, description="Source classification"),
) -> ExtractionResponse:
    content_type = request.headers.get("content-type", "")

    # 1. JSON Request handling
    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception as json_err:
            raise ValidationError(f"Malformed JSON request: {json_err}") from json_err

        raw_text = body.get("text")
        if raw_text is None or not str(raw_text).strip():
            raise ValidationError("Pasted text content cannot be empty or whitespace only.")
        raw_source = body.get("source_type")
        source = (
            DeviationSource(raw_source)
            if raw_source in DeviationSource._value2member_map_
            else DeviationSource.TEXT
        )
        return service.normalize_text(raw_text, declared_source=source)

    # 2. File Upload handling
    if file is not None and file.filename:
        return await service.extract_from_file(file)

    # 3. Form-data Text handling
    if text is not None:
        if not text.strip():
            raise ValidationError("Pasted text content cannot be empty or whitespace only.")
        return service.normalize_text(text, declared_source=source_type)

    # 4. Neither file nor text provided -> Malformed request
    raise PharmaOneError("Malformed request: either a document file ('file') or text content ('text') must be provided.")


@router.post(
    "/process",
    response_model=ProcessResponse,
    summary="Process raw deviation content and return AI extraction + assessment",
)
async def process_deviation(
    payload: ProcessRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ProcessResponse:
    """AI Deviation Assistant. Authenticated enterprise endpoint."""
    return await run_ai_deviation_pipeline(
        content=payload.content,
        source=payload.source,
    )


@router.post(
    "/chat",
    response_model=DeviationChatResponse,
    summary="Context-aware chat for deviation intake",
)
async def chat_deviation(
    payload: DeviationChatRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DeviationChatResponse:
    """Answer questions about the deviation grounded in extracted context and current form."""
    return await answer_deviation_chat(payload)



@router.post(
    "",
    response_model=DeviationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a final, user-reviewed deviation",
)
async def create_deviation(
    payload: DeviationCreate,
    service: DeviationServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DeviationRead:
    """Create deviation scoped strictly to authenticated company."""
    deviation = await service.create(payload, user=current_user)
    return DeviationRead.model_validate(deviation)


@router.get("", response_model=DeviationList, summary="List deviations")
async def list_deviations(
    service: DeviationServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: DeviationStatus | None = Query(default=None, alias="status"),
    severity: Severity | None = Query(default=None),
    deviation_type: DeviationType | None = Query(default=None),
) -> DeviationList:
    """List deviations with company data isolation."""
    items, total = await service.list(
        limit=limit,
        offset=offset,
        company_id=current_user.company_id,
        status=status_filter,
        severity=severity,
        deviation_type=deviation_type,
    )
    return DeviationList(
        items=[DeviationRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{deviation_id}", response_model=DeviationRead, summary="Get a deviation")
async def get_deviation(
    deviation_id: UUID,
    service: DeviationServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DeviationRead:
    """Get deviation ensuring tenant isolation."""
    deviation = await service.get(deviation_id, company_id=current_user.company_id)
    return DeviationRead.model_validate(deviation)


@router.put("/{deviation_id}", response_model=DeviationRead, summary="Update a reviewed deviation")
async def update_deviation(
    deviation_id: UUID,
    payload: DeviationUpdate,
    service: DeviationServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DeviationRead:
    """Update deviation ensuring tenant isolation."""
    deviation = await service.update(deviation_id, payload, user=current_user)
    return DeviationRead.model_validate(deviation)


@router.post(
    "/{deviation_id}/confirm-severity",
    response_model=DeviationRead,
    summary="QA human review and confirmation of AI advisory severity & impact",
)
async def confirm_deviation_severity(
    deviation_id: UUID,
    payload: DeviationSeverityConfirm,
    service: DeviationServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> DeviationRead:
    """Record authoritative QA human decision on AI-suggested severity and impact."""
    deviation = await service.confirm_severity(deviation_id, payload, user=current_user)
    return DeviationRead.model_validate(deviation)


@router.delete(
    "/{deviation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a deviation",
)
async def delete_deviation(
    deviation_id: UUID,
    service: DeviationServiceDep,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    """Delete deviation ensuring tenant isolation."""
    await service.delete(deviation_id, company_id=current_user.company_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

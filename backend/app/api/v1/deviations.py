from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.deps import DeviationServiceDep, ProcessingServiceDep
from app.core.enums import DeviationStatus, DeviationType, Severity
from app.schemas.deviation import (
    DeviationCreate,
    DeviationList,
    DeviationRead,
    DeviationUpdate,
)
from app.schemas.process import ProcessRequest, ProcessResponse

router = APIRouter(prefix="/deviations", tags=["deviations"])


@router.post(
    "/process",
    response_model=ProcessResponse,
    summary="Process raw deviation content and return AI extraction + assessment",
)
async def process_deviation(
    payload: ProcessRequest,
    service: ProcessingServiceDep,
) -> ProcessResponse:
    """AI Deviation Assistant. Returns a structured extraction and an AI risk
    assessment for the reporter to review and edit. Nothing is persisted here —
    human review is required before saving (`POST /deviations`).

    NOTE: this foundation returns an offline heuristic stub (`is_stub=true`);
    the live LangGraph + Groq + RAG pipeline plugs in behind the same contract.
    """
    return await service.process(payload)


@router.post(
    "",
    response_model=DeviationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a final, user-reviewed deviation",
)
async def create_deviation(
    payload: DeviationCreate,
    service: DeviationServiceDep,
) -> DeviationRead:
    deviation = await service.create(payload)
    return DeviationRead.model_validate(deviation)


@router.get("", response_model=DeviationList, summary="List deviations")
async def list_deviations(
    service: DeviationServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: DeviationStatus | None = Query(default=None, alias="status"),
    severity: Severity | None = Query(default=None),
    deviation_type: DeviationType | None = Query(default=None),
) -> DeviationList:
    items, total = await service.list(
        limit=limit,
        offset=offset,
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
) -> DeviationRead:
    deviation = await service.get(deviation_id)
    return DeviationRead.model_validate(deviation)


@router.put("/{deviation_id}", response_model=DeviationRead, summary="Update a reviewed deviation")
async def update_deviation(
    deviation_id: UUID,
    payload: DeviationUpdate,
    service: DeviationServiceDep,
) -> DeviationRead:
    deviation = await service.update(deviation_id, payload)
    return DeviationRead.model_validate(deviation)


@router.delete(
    "/{deviation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a deviation",
)
async def delete_deviation(
    deviation_id: UUID,
    service: DeviationServiceDep,
) -> Response:
    await service.delete(deviation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from app.schemas.process import ProcessRequest, ProcessResponse
from app.workflows import deviation_intake


class ProcessingService:
    """Fronts the AI orchestration workflow so the API layer stays decoupled
    from the workflow implementation (stub today, LangGraph+Groq later)."""

    async def process(self, request: ProcessRequest) -> ProcessResponse:
        return await deviation_intake.process_deviation(
            content=request.content,
            source=request.source,
        )

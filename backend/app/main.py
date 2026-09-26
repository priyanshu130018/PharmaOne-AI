from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    DocumentExtractionError,
    EmptyPdfError,
    FileTooLargeError,
    InvalidPdfError,
    NotFoundError,
    PharmaOneError,
    UnsupportedFileTypeError,
    ValidationError,
)
from app.core.logging import configure_logging, get_logger
from app.schemas.common import HealthStatus

logger = get_logger("pharmaone")

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate configuration at startup (fail fast if env is incomplete).
    settings = get_settings()
    configure_logging()
    logger.info("Starting PharmaOne AI API in '%s' environment", settings.ENVIRONMENT)
    yield
    from app.db.session import dispose_engine

    await dispose_engine()
    logger.info("PharmaOne AI API shut down cleanly")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="PharmaOne AI — Deviation Intake API",
        description="Backend for the AIVOA AI-Powered Deviation Intake module.",
        version="0.1.0",
        lifespan=lifespan,
        servers=[{"url": settings.API_BASE_URL}],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(NotFoundError)
    async def _not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": exc.message})

    @app.exception_handler(UnsupportedFileTypeError)
    async def _unsupported_file_handler(_: Request, exc: UnsupportedFileTypeError) -> JSONResponse:
        return JSONResponse(status_code=415, content={"detail": exc.message})

    @app.exception_handler(FileTooLargeError)
    async def _file_too_large_handler(_: Request, exc: FileTooLargeError) -> JSONResponse:
        return JSONResponse(status_code=413, content={"detail": exc.message})

    @app.exception_handler(InvalidPdfError)
    async def _invalid_pdf_handler(_: Request, exc: InvalidPdfError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.message})

    @app.exception_handler(EmptyPdfError)
    async def _empty_pdf_handler(_: Request, exc: EmptyPdfError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.message})

    @app.exception_handler(DocumentExtractionError)
    async def _extraction_error_handler(_: Request, exc: DocumentExtractionError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.message})

    @app.exception_handler(ValidationError)
    async def _validation_handler(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.message})

    @app.exception_handler(PharmaOneError)
    async def _domain_handler(_: Request, exc: PharmaOneError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": exc.message})

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Please try again or contact support."},
        )

    @app.get("/health", response_model=HealthStatus, tags=["meta"], summary="Liveness probe root alias")
    async def root_health() -> HealthStatus:
        return HealthStatus(status="ok", environment=settings.ENVIRONMENT, version="0.1.0")

    @app.get("/", tags=["meta"], summary="API root")
    async def root() -> dict[str, str]:
        return {
            "name": "PharmaOne AI — Deviation Intake API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": f"{API_PREFIX}/health",
        }

    app.include_router(api_router, prefix=API_PREFIX)
    return app


app = create_app()

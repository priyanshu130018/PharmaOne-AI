from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, PharmaOneError, ValidationError
from app.core.logging import configure_logging, get_logger

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
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(NotFoundError)
    async def _not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": exc.message})

    @app.exception_handler(ValidationError)
    async def _validation_handler(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.message})

    @app.exception_handler(PharmaOneError)
    async def _domain_handler(_: Request, exc: PharmaOneError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": exc.message})

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

# from prometheus_fastapi_instrumentator import Instrumentator
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from structlog.contextvars import merge_contextvars

from app.api import api_router
from app.core.lifespan import lifespan
from app.core.middleware import RequestIDMiddleware, TimingMiddleware
from app.core.settings import settings

# Initialize Structlog
structlog.configure(
    processors=[
        merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()


def create_app() -> FastAPI:
    """Application factory to initialize and configure the FastAPI app."""

    # Instantiate FastAPI with the lifespan manager
    app = FastAPI(
        title=settings.name,
        docs_url="/docs" if settings.env != "prod" else None,  # Hide docs in prod
        openapi_url="/openapi.json" if settings.env != "prod" else None,
        lifespan=lifespan,
    )

    # * Add Middleware (Order matters! First added is last to execute)

    # Gzip: Innermost middleware, Compress the final response payload
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    # CORS: Handles preflight OPTIONS requests before anything else.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Timing: Measures the time taken by CORS, GZip, and the App.
    app.add_middleware(TimingMiddleware)
    # RequestID: Outermost layer. Generates ID first so ALL logs have it.
    app.add_middleware(RequestIDMiddleware)

    # ? Prometheus Metrics (Instrumentator)
    # This exposes /metrics endpoint for Prometheus to scrape
    # Instrumentator().instrument(app).expose(
    #   app, endpoint="/metrics"
    # ) #! TODO: FOR TEST COMMENT OUT

    # Include the grouped API routers
    app.include_router(api_router, prefix="/api/v1")

    # Root health check endpoint
    @app.get("/health", tags=["System"])
    async def health_check() -> dict[str, str]:
        """Simple health check endpoint"""
        logger.info("Health check endpoint")
        return {"status": "healthy", "environment": settings.env}

    logger.info("FastAPI application factory executed")
    return app


app = create_app()

# from prometheus_fastapi_instrumentator import Instrumentator
from collections.abc import Mapping, MutableMapping
from typing import Annotated, Any

import structlog
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from opentelemetry import trace
from prometheus_fastapi_instrumentator import Instrumentator
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.contextvars import merge_contextvars

from app.api import api_router
from app.core.dependencies import get_redis_client
from app.core.lifespan import lifespan
from app.core.middleware import RequestIDMiddleware, TimingMiddleware
from app.core.settings import settings
from app.core.tracing import setup_tracing
from app.db.session import get_db


# ? Custom processor to injct OTel trace_id into logs
def inject_trace_info(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> Mapping[str, Any]:
    span = trace.get_current_span()
    if span and span.is_recording():
        context = span.get_span_context()
        event_dict["trace_id"] = f"{context.trace_id:x}"
        event_dict["span_id"] = f"{context.span_id:x}"
    return event_dict


# Initialize Structlog
structlog.configure(
    processors=[
        merge_contextvars,
        inject_trace_info,
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

    # Setup OpenTelemetry Tracing
    setup_tracing(app)

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
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    # Include the grouped API routers
    app.include_router(api_router, prefix="/api/v1")

    # Liveness Probe: Just checks if the process is alive
    @app.get("/healthz", tags=["System"])
    async def liveness() -> dict[str, str]:
        """
        Liveness probe. If this fails, the orchestrator restarts the container.
        """
        logger.info("Health check endpoint")
        return {"status": "healthy"}

    @app.get("/readyz", tags=["System"])
    async def readiness(
        db: Annotated[AsyncSession, Depends(get_db)],
        redis: Annotated[Redis, Depends(get_redis_client)],
    ) -> dict[str, str]:
        """
        Readiness probe. If this fails, the orchestrator stops routing traffic.
        """
        await db.execute(text("SELECT 1"))
        await redis.ping()
        return {"status": "ready", "database": "connected", "redis": "connected"}

    logger.info("FastAPI application factory executed")
    return app


app = create_app()

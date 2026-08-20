# from prometheus_fastapi_instrumentator import Instrumentator
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.lifespan import lifespan
from app.core.settings import settings

# Initialize Structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()


def create_app() -> FastAPI:
    """Application factory to initialize and configure the FastAPI app."""

    # 1. Instantiate FastAPI with the lifespan manager
    app = FastAPI(
        title=settings.name,
        docs_url="/docs" if settings.env != "prod" else None,  # Hide docs in prod
        openapi_url="/openapi.json" if settings.env != "prod" else None,
        lifespan=lifespan,
    )

    # 2. Add Middleware (Order matters! First added is last to execute)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  #! TODO: tighten in prod
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Prometheus Metrics (Instrumentator)
    # This exposes /metrics endpoint for Prometheus to scrape
    # Instrumentator().instrument(app).expose(
    #   app, endpoint="/metrics"
    # ) #! TODO: FOR TEST COMMENT OUT

    # 4. Include the grouped API routers
    app.include_router(api_router, prefix="/api/v1")

    # 5. Root health check endpoint
    @app.get("/health", tags=["System"])  # type: ignore[misc]
    async def health_check() -> dict[str, str]:
        """Simple health check endpoint"""
        return {"status": "healthy", "environment": settings.env}

    logger.info("FastAPI application factory executed")
    return app


app = create_app()

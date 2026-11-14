from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.settings import settings
from app.db.session import engine


def setup_tracing(app: FastAPI) -> None:
    """Initializes OpenTelemetry and instruments FastAPI and SQLAlchemy."""
    resource = Resource.create({"service.name": settings.otel.service_name})
    provider = TracerProvider(resource=resource)

    # * Export traces to the OTel Collector (using URL from settings)
    otlp_exporter = OTLPSpanExporter(endpoint=settings.otel.endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(provider)

    # ? Auto-instrument Fastapi(create a span for every HTTP req)
    FastAPIInstrumentor.instrument_app(app)

    # ? Auto-instrument SQLAlchemy (creates a span for every DB query)
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)

    # ? Auto-instrument Redis
    RedisInstrumentor().instrument()

import asyncio
import json
from datetime import datetime, timezone

import dramatiq
import redis
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import CurrentMessage
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry_instrumentor_dramatiq import DramatiqInstrumentor
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.settings import settings
from app.schemas.webhook import WebhookPayload
from app.services.reservation import expire_stale_reservations
from app.services.webhook import process_payment_webhook

# * Setup OTel for the worker process
resource = Resource.create({"service.name": f"{settings.otel.service_name}-worker"})
provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(endpoint=settings.otel.endpoint, insecure=True)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)
# * Get Tracer for manual spans
tracer = trace.get_tracer(__name__)

# ? AUTO-INSTRUMENT DRAMATIQ! This handles context propagation!
DramatiqInstrumentor().instrument()

# * Create dedicated engine for the worker using NullPoll
# * This prevent the 'attached to a different loop' error
worker_engine = create_async_engine(str(settings.db.async_dsn), poolclass=NullPool)
WorkerSessionLocal = async_sessionmaker(
    bind=worker_engine, class_=AsyncSession, expire_on_commit=False
)

# * Initialize the Redis Broker
broker = RedisBroker(url=str(settings.redis.url))  # type: ignore
dramatiq.set_broker(broker)
broker.add_middleware(CurrentMessage())

# ? A Redis Client to store dead letters for inspection
dead_letter_redis = redis.from_url(str(settings.redis.url), decode_responses=True)


# * Define the Background actor
@dramatiq.actor(max_retries=3)
def send_confirmation_email(reservation_id: int) -> None:
    """
    In a real app, this would query the DB for the user's email,
    render an HTML template, and send it via SMTP.
    For MVP, we just log it to prove the background task worked.
    """
    print(f"[WORKER] Sending confirmation email for reservation {reservation_id}...")
    # TODO: query db, send email


# * Webhook processing actor
@dramatiq.actor(max_retries=3, min_backoff=2000)
def process_webhook_event(payload_json: str) -> None:
    """
    Processes the webhook in the background.
    If this fails (e.g. DB is down), Dramatiq retries it.
    If it fails 3 times, it goes to the dead-letter queue.
    """
    try:
        # * We use asyncio.run to call our async service layer form sync Dramatiq
        asyncio.run(_process_webhook_async(payload_json))
    except Exception as e:
        # We need access to the message to check the retry count
        message = CurrentMessage.get_current_message()
        if message is not None:
            retries = message.options.get("retries", 0)
            max_retries = message.options.get("max_retries", 0)

            # if it was the last retry,save it to the dead letter queue for inspection
            if retries >= max_retries:
                print("[WORKER] Dead lettering webhook event...")
                dead_letter_data = json.dumps(
                    {
                        "payload": payload_json,
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
                # ? Push to a redis list called "dead_letters"
                dead_letter_redis.rpush("dead_letters", dead_letter_data)
        # Re-raise the exception so Dramatiq knows it failed
        raise


async def _process_webhook_async(payload_json: str) -> None:
    payload = WebhookPayload.model_validate_json(payload_json)
    # * Create a fresh DB session for the background worker
    async with WorkerSessionLocal() as db:
        await process_payment_webhook(db, payload)


# Sweeper for stale reservations
@dramatiq.actor
def expire_pending_reservations() -> None:
    """Periodic job to expire stale reservations"""
    print("[WORKER] Running stale reservation sweeper...")
    asyncio.run(_expire_stale_reservations_async())


async def _expire_stale_reservations_async() -> None:
    async with WorkerSessionLocal() as db:
        count = await expire_stale_reservations(db)
        if count > 0:
            print(f"[WORKER] Expired {count} stale reservations.")
        else:
            print("[WORKER] No stale reservations found.")

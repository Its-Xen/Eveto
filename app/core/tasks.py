import asyncio
import json
from datetime import datetime, timezone

import dramatiq
import redis
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import CurrentMessage

from app.core.settings import settings
from app.db.session import AsyncSessionLocal
from app.schemas.webhook import WebhookPayload
from app.services.reservation import expire_stale_reservations
from app.services.webhook import process_payment_webhook

# * Initialize the Redis Broker
broker = RedisBroker(url=str(settings.redis.url))  # type: ignore
dramatiq.set_broker(broker)

# ? Install the CurrentMessage middleware
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
        assert message is not None  # ? FIX: Assert to satisfy Mypy
        retries = message.options.get("retries", 0)
        max_retries = message.options.get("max_retries", 0)

        # if this was the last retry, save it to the dead letter queue for inspection
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
    async with AsyncSessionLocal() as db:
        await process_payment_webhook(db, payload)


# Sweeper for stale reservations
@dramatiq.actor
def expire_pending_reservations() -> None:
    """Periodic job to expire stale reservations"""
    print("[WORKER] Running stale reservation sweeper...")
    asyncio.run(_expire_stale_reservations_async())


async def _expire_stale_reservations_async() -> None:
    async with AsyncSessionLocal() as db:
        count = await expire_stale_reservations(db)
        if count > 0:
            print(f"[WORKER] Expired {count} stale reservations.")
        else:
            print("[WORKER] No stale reservations found.")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_event import WebhookEvent


async def get_webhook_by_provider_id(
    db: AsyncSession, provider_event_id: str
) -> WebhookEvent | None:
    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.provider_event_id == provider_event_id)
    )
    return result.scalar_one_or_none()


async def create_webhook_event(
    db: AsyncSession, provider_event_id: str, payload: str
) -> WebhookEvent:
    db_event = WebhookEvent(provider_event_id=provider_event_id, payload=payload)
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event

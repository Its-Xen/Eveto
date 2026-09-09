from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.event import Event
from app.repositories.event import (
    create_event,
    delete_event,
    get_all_events,
    get_event_by_id,
    get_published_event_by_id,
    get_published_events,
    update_event,
)
from app.schemas.event import EventCreate, EventUpdate


async def get_events(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Event]:
    return await get_all_events(db, skip, limit)


async def get_event(db: AsyncSession, event_id: int) -> Event:
    event = await get_event_by_id(db, event_id)
    if not event:
        raise NotFoundError(detail="Event not found")
    return event


async def list_published_events(db: AsyncSession, skip: int, limit: int) -> list[Event]:
    return await get_published_events(db, skip, limit)


async def get_published_event_or_404(db: AsyncSession, event_id: int) -> Event:
    event = await get_published_event_by_id(db, event_id)
    if not event:
        raise NotFoundError(detail="Event not found")
    return event


async def create_new_event(
    db: AsyncSession, event_in: EventCreate, user_id: int
) -> Event:
    return await create_event(db, event_in.model_dump(), user_id)


async def update_existing_event(
    db: AsyncSession, event_id: int, event_in: EventUpdate
) -> Event:
    db_event = await get_event(db, event_id)
    update_data = event_in.model_dump(exclude_unset=True)
    return await update_event(db, db_event, update_data)


async def delete_existing_event(db: AsyncSession, event_id: int) -> None:
    db_event = await get_event(db, event_id)
    await delete_event(db, db_event)

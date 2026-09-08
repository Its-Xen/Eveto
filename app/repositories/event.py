from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event


async def get_event_by_id(db: AsyncSession, event_id: int) -> Event | None:
    result = await db.execute(select(Event).where(Event.id == event_id))
    return result.scalar_one_or_none()


async def get_all_events(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[Event]:
    result = await db.execute(select(Event).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_event(
    db: AsyncSession, event_data: dict[str, Any], user_id: int
) -> Event:
    event = Event(**event_data, created_by_id=user_id)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def update_event(
    db: AsyncSession, db_event: Event, update_data: dict[str, Any]
) -> Event:
    for field, value in update_data.items():
        setattr(db_event, field, value)

    await db.commit()
    await db.refresh(db_event)
    return db_event


async def delete_event(db: AsyncSession, db_event: Event) -> None:
    await db.delete(db_event)
    await db.commit()

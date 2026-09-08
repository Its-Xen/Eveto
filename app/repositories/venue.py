from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Venue


async def get_venue_by_id(db: AsyncSession, venue_id: int) -> Venue | None:
    result = await db.execute(select(Venue).where(Venue.id == venue_id))
    return result.scalar_one_or_none()


async def get_all_venues(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[Venue]:
    result = await db.execute(select(Venue).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_venue(
    db: AsyncSession, venue_data: dict[str, Any], user_id: int
) -> Venue:
    venue = Venue(**venue_data, created_by_id=user_id)
    db.add(venue)
    await db.commit()
    await db.refresh(venue)
    return venue


async def update_venue(
    db: AsyncSession, db_venue: Venue, update_data: dict[str, Any]
) -> Venue:
    for field, value in update_data.items():
        setattr(db_venue, field, value)
    await db.commit()
    await db.refresh(db_venue)
    return db_venue


async def delete_venue(db: AsyncSession, db_venue: Venue) -> None:
    await db.delete(db_venue)
    await db.commit()

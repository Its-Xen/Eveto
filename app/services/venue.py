from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models import Venue
from app.repositories.venue import (
    create_venue,
    delete_venue,
    get_all_venues,
    get_venue_by_id,
    update_venue,
)
from app.schemas.venue import VenueCreate, VenueUpdate


async def get_venues(db: AsyncSession, skip: int, limit: int) -> list[Venue]:
    return await get_all_venues(db, skip, limit)


async def get_venue(db: AsyncSession, venue_id: int) -> Venue:
    venue = await get_venue_by_id(db, venue_id)
    if not venue:
        raise NotFoundError(detail=f"Venue with id {venue_id} not found")
    return venue


async def create_new_venue(
    db: AsyncSession, venue_in: VenueCreate, user_id: int
) -> Venue:
    return await create_venue(db, venue_in.model_dump(), user_id)


async def update_existing_venue(
    db: AsyncSession, venue_in: VenueUpdate, venue_id: int
) -> Venue:
    db_venue = await get_venue(db, venue_id)
    update_data = venue_in.model_dump(
        exclude_unset=True
    )  # * Only update fields that were actually sent
    return await update_venue(db, db_venue, update_data)


async def delete_existing_venue(db: AsyncSession, venue_id: int) -> None:
    db_venue = await get_venue(db, venue_id)
    return await delete_venue(db, db_venue)

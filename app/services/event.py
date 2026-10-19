import json
from typing import Any, cast

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.settings import settings
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
from app.schemas.event import EventCreate, EventRead, EventUpdate


#! Setup Cache Version
async def _get_cache_version(redis: Redis) -> int:
    """Helper to fetch current cache version."""
    version = await redis.get("events:version")
    return int(version) if version else 1


#! Explicit Invalidation
async def invalidate_event_cache(redis: Redis) -> None:
    """Call this on Create/Update/Delete to instantly invalidate all event caches."""
    await redis.incr("events:version")


async def get_events(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Event]:
    return await get_all_events(db, skip, limit)


async def get_event(db: AsyncSession, event_id: int) -> Event:
    event = await get_event_by_id(db, event_id)
    if not event:
        raise NotFoundError(detail="Event not found")
    return event


async def list_published_events(
    db: AsyncSession, redis: Redis, skip: int, limit: int
) -> list[dict[str, Any]]:
    """Cache-aside logic for listing published events."""
    version = await _get_cache_version(redis)
    cache_key = f"events:list:v{version}:{skip}:{limit}"

    # * Check Cache
    cached = await redis.get(cache_key)
    if cached:
        # ? Use cast to tell mypy exactly what json.loads is returning
        return cast(list[dict[str, Any]], json.loads(cached))  # Cache Hit

    # * Check Cache Miss
    events = await get_published_events(db, skip, limit)
    events_data = [EventRead.model_validate(e).model_dump(mode="json") for e in events]

    # * Set Cache
    await redis.set(cache_key, json.dumps(events_data), ex=settings.redis.cache_ttl)
    return events_data


async def get_published_event_or_404(
    db: AsyncSession, redis: Redis, event_id: int
) -> dict[str, Any]:
    """Cache-aside logic for a single published event."""
    version = await _get_cache_version(redis)
    cached_key = f"events:v{version}:{event_id}"

    cached = await redis.get(cached_key)
    if cached:
        return cast(dict[str, Any], json.loads(cached))  # Cache Hit

    # * Query for cache miss
    event = await get_published_event_by_id(db, event_id)
    if not event:
        raise NotFoundError(detail="Event not found")

    # * Validate data and set it to redis
    event_data = EventRead.model_validate(event).model_dump(mode="json")
    await redis.set(cached_key, json.dumps(event_data), ex=settings.redis.cache_ttl)

    return event_data


async def create_new_event(
    db: AsyncSession, event_in: EventCreate, user_id: int, redis: Redis
) -> Event:
    result = await create_event(db, event_in.model_dump(), user_id)
    await invalidate_event_cache(redis)  #! Invalidate AFTER DB write
    return result


async def update_existing_event(
    db: AsyncSession, event_id: int, event_in: EventUpdate, redis: Redis
) -> Event:
    db_event = await get_event(db, event_id)
    update_data = event_in.model_dump(exclude_unset=True)
    result = await update_event(db, db_event, update_data)
    await invalidate_event_cache(redis)  #! Invalidate AFTER DB write
    return result


async def delete_existing_event(db: AsyncSession, event_id: int, redis: Redis) -> None:
    db_event = await get_event(db, event_id)
    await delete_event(db, db_event)
    await invalidate_event_cache(redis)  #! Invalidate AFTER DB write

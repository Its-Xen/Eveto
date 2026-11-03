from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_api_key_user, get_redis_client
from app.core.rate_limit import check_redis_rate_limit
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.schemas.event import EventRead
from app.services.event import list_published_events

router = APIRouter()


@router.get("/events", response_model=list[EventRead])
async def partner_list_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    api_key: Annotated[ApiKey, Depends(get_api_key_user)],
    _rate_limit: Annotated[None, Depends(check_redis_rate_limit)] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=0, le=100),
) -> list[dict[str, Any]]:
    """Partner endpoint: List all published events."""
    return await list_published_events(db, redis, skip, limit)

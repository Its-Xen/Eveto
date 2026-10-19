from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import check_rate_limit
from app.db.session import get_db
from app.schemas.event import EventRead
from app.services.event import get_published_event_or_404, list_published_events

router = APIRouter()


@router.get("", response_model=list[EventRead])
async def list_events(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _rate_limit: Annotated[None, Depends(check_rate_limit)],
    skip: int = 0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Public endpoint: List all published events."""
    redis = request.app.state.redis
    return await list_published_events(db, redis, skip, limit)


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _rate_limit: Annotated[None, Depends(check_rate_limit)],
) -> dict[str, Any]:
    """Public endpoint: Get a single published event."""
    redis = request.app.state.redis
    return await get_published_event_or_404(db, redis, event_id)

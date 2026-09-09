from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.event import Event
from app.schemas.event import EventRead
from app.services.event import get_published_event_or_404, list_published_events

router = APIRouter()


@router.get("", response_model=list[EventRead])
async def list_events(
    db: Annotated[AsyncSession, Depends(get_db)], skip: int = 0, limit: int = 100
) -> list[Event]:
    """Public endpoint: List all published events."""
    return await list_published_events(db, skip, limit)


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Event:
    """Public endpoint: Get a single published event."""
    return await get_published_event_or_404(db, event_id)

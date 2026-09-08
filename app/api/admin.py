from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.event import Event
from app.models.ticket_type import TicketType
from app.models.user import User, UserRole
from app.models.venue import Venue
from app.schemas.event import EventCreate, EventRead, EventUpdate
from app.schemas.ticket_type import TicketTypeCreate, TicketTypeRead, TicketTypeUpdate
from app.schemas.venue import VenueCreate, VenueRead, VenueUpdate
from app.services.event import (
    create_new_event,
    delete_existing_event,
    get_events,
    update_existing_event,
)
from app.services.ticket_type import (
    create_new_ticket_type,
    delete_existing_ticket_type,
    get_ticket_types,
    update_existing_ticket_type,
)
from app.services.venue import (
    create_new_venue,
    delete_existing_venue,
    get_venues,
    update_existing_venue,
)

router = APIRouter()


# * Venue Routes
@router.get("/venues", response_model=list[VenueRead])
async def admin_list_venues(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    skip: int = 0,
    limit: int = 100,
) -> list[Venue]:
    return await get_venues(db, skip, limit)


@router.post("/venues", response_model=VenueRead, status_code=status.HTTP_201_CREATED)
async def create_venue_api(
    venue_in: VenueCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> Venue:
    return await create_new_venue(db, venue_in, current_user.id)


@router.patch("/venues/{venue_id}", response_model=VenueRead)
async def update_venue_api(
    venue_id: int,
    venue_in: VenueUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> Venue:
    return await update_existing_venue(db, venue_in, venue_id)


@router.delete("/venues/{venue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_venue_api(
    venue_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> None:
    await delete_existing_venue(db, venue_id)
    return None


# * Event Routes
@router.get("/events", response_model=list[EventRead])
async def admin_list_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    skip: int = 0,
    limit: int = 100,
) -> list[Event]:
    return await get_events(db, skip, limit)


@router.post("/events", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event_api(
    event_in: EventCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> Event:
    return await create_new_event(db, event_in, current_user.id)


@router.patch("/events/{event_id}", response_model=EventRead)
async def update_event_api(
    event_id: int,
    event_in: EventUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> Event:
    return await update_existing_event(db, event_id, event_in)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event_api(
    event_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> None:
    await delete_existing_event(db, event_id)
    return None


# * TicketType Routes
@router.get("/ticket-types", response_model=list[TicketTypeRead])
async def admin_list_ticket_types(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    skip: int = 0,
    limit: int = 100,
) -> list[TicketType]:
    return await get_ticket_types(db, skip, limit)


@router.post(
    "/ticket-types", response_model=TicketTypeRead, status_code=status.HTTP_201_CREATED
)
async def create_ticket_type_api(
    ticket_in: TicketTypeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> TicketType:
    return await create_new_ticket_type(db, ticket_in)


@router.patch("/ticket-types/{ticket_type_id}", response_model=TicketTypeRead)
async def update_ticket_type_api(
    ticket_type_id: int,
    ticket_in: TicketTypeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> TicketType:
    return await update_existing_ticket_type(db, ticket_type_id, ticket_in)


@router.delete("/ticket-types/{ticket_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket_type_api(
    ticket_type_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> None:
    await delete_existing_ticket_type(db, ticket_type_id)
    return None

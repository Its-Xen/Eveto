from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.ticket_type import TicketType
from app.repositories.event import get_event_by_id
from app.repositories.ticket_type import (
    create_ticket_type,
    delete_ticket_type,
    get_all_ticket_types,
    get_ticket_type_by_id,
    update_ticket_type,
)
from app.schemas.ticket_type import TicketTypeCreate, TicketTypeUpdate


async def get_ticket_types(db: AsyncSession, skip: int, limit: int) -> list[TicketType]:
    return await get_all_ticket_types(db, skip, limit)


async def get_ticket_type(db: AsyncSession, ticket_type_id: int) -> TicketType:
    ticket = await get_ticket_type_by_id(db, ticket_type_id)
    if not ticket:
        raise NotFoundError(detail="TicketType not found")
    return ticket


async def create_new_ticket_type(
    db: AsyncSession, ticket_in: TicketTypeCreate
) -> TicketType:
    # Business Logic: Verify the Event exists before adding tickets to it!
    event = await get_event_by_id(db, ticket_in.event_id)
    if not event:
        raise NotFoundError(detail=f"Event with id {ticket_in.event_id} not found")

    return await create_ticket_type(db, ticket_in.model_dump())


async def update_existing_ticket_type(
    db: AsyncSession, ticket_type_id: int, ticket_in: TicketTypeUpdate
) -> TicketType:
    db_ticket = await get_ticket_type(db, ticket_type_id)
    update_data = ticket_in.model_dump(exclude_unset=True)
    return await update_ticket_type(db, db_ticket, update_data)


async def delete_existing_ticket_type(db: AsyncSession, ticket_type_id: int) -> None:
    db_ticket = await get_ticket_type(db, ticket_type_id)
    await delete_ticket_type(db, db_ticket)

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket_type import TicketType


async def get_ticket_type_by_id(
    db: AsyncSession, ticket_type_id: int
) -> TicketType | None:
    result = await db.execute(select(TicketType).where(TicketType.id == ticket_type_id))
    return result.scalar_one_or_none()


async def get_all_ticket_types(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[TicketType]:
    result = await db.execute(select(TicketType).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_ticket_type(
    db: AsyncSession, ticket_data: dict[str, Any]
) -> TicketType:
    db_ticket = TicketType(**ticket_data)
    db.add(db_ticket)
    await db.commit()
    await db.refresh(db_ticket)
    return db_ticket


async def update_ticket_type(
    db: AsyncSession, db_ticket: TicketType, update_data: dict[str, Any]
) -> TicketType:
    for field, value in update_data.items():
        setattr(db_ticket, field, value)
    await db.commit()
    await db.refresh(db_ticket)
    return db_ticket


async def delete_ticket_type(db: AsyncSession, db_ticket: TicketType) -> None:
    await db.delete(db_ticket)
    await db.commit()

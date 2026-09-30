from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reservation import Reservation, ReservationStatus
from app.models.ticket_type import TicketType


async def get_ticket_type_for_update(
    db: AsyncSession, ticket_type_id: int
) -> TicketType | None:
    """Fetches a ticket type AND locks the row for the duration of the transaction."""
    stmt = select(TicketType).where(TicketType.id == ticket_type_id).with_for_update()
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_reservation_by_id(
    db: AsyncSession, reservation_id: int
) -> Reservation | None:
    result = await db.execute(
        select(Reservation).where(Reservation.id == reservation_id)
    )
    return result.scalar_one_or_none()


async def create_reservation(
    db: AsyncSession, reservation_data: dict[str, Any]
) -> Reservation:
    db_reservation = Reservation(**reservation_data)
    db.add(db_reservation)
    await db.commit()
    await db.refresh(db_reservation)
    return db_reservation


async def save_changes(db: AsyncSession, db_obj: Any) -> None:
    """Helper to commit and refresh changes to an existing object
    (like TicketType or Reservation)."""
    await db.commit()
    await db.refresh(db_obj)


async def get_reservation_by_idempotency_key(
    db: AsyncSession, key: str
) -> Reservation | None:
    """Find a reservation by its idempotency key to prevent double-charging."""
    result = await db.execute(
        select(Reservation).where(Reservation.idempotency_key == key)
    )
    return result.scalar_one_or_none()


async def get_expired_reservations(db: AsyncSession) -> list[Reservation]:
    """Find all pending reservations that have passed their expiry time."""
    now = datetime.now(timezone.utc)
    stmt = select(Reservation).where(
        Reservation.status == ReservationStatus.pending, Reservation.expires_at <= now
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

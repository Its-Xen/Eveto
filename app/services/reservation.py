from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.reservation import Reservation, ReservationStatus
from app.repositories.reservation import (
    create_reservation,
    get_reservation_by_id,
    get_reservation_by_idempotency_key,
    get_ticket_type_for_update,
    save_changes,
)
from app.schemas.reservation import ReservationCreate


async def create_new_reservation(
    db: AsyncSession,
    reservation_in: ReservationCreate,
    user_id: int,
    idempotency_key: str | None = None,
) -> Reservation:
    """Bussiness logic for creating a reservation
    with pessimistic locking and idempotency."""

    if idempotency_key:
        existing_reservation = await get_reservation_by_idempotency_key(
            db, idempotency_key
        )
        if existing_reservation:
            # Return the original reservation without doing it again.
            return existing_reservation

    ticket_type = await get_ticket_type_for_update(db, reservation_in.ticket_type_id)

    if not ticket_type:
        raise NotFoundError(detail="Ticket type not found.")

    # * Check Availability
    if ticket_type.available_quantity < reservation_in.quantity:
        detail_msg = (
            f"Not enough tickets available. "
            f"Requested: {reservation_in.quantity}, "
            f"Available: {ticket_type.available_quantity}"
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail_msg)

    # * Mutate the ticket type (Increment reserved quantiy)
    ticket_type.reserved_quantity += reservation_in.quantity

    # * prepare reservation data and call repo to create it
    reservation_data = {
        "user_id": user_id,
        "ticket_type_id": reservation_in.ticket_type_id,
        "quantity": reservation_in.quantity,
        "status": ReservationStatus.pending,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=15),  # TTL Hold!
        "idempotency_key": idempotency_key,
    }
    # ? Note: Because we changed ticket_type, calling create_reservation (which commits)
    # * will also flush the ticket_type update to the database automatically!
    return await create_reservation(db, reservation_data)


async def cancel_exsiting_reservation(
    db: AsyncSession, reservation_id: int, user_id: int
) -> Reservation:
    """Business logic for cancelling a reservation and releasing inventory."""
    reservation = await get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise NotFoundError(detail="Reservation not found.")

    # * Ownership and status checks
    if reservation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this reservation",
        )
    if reservation.status != ReservationStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation is not pending"
        )

    # * Call repo to fetch and lock the ticket type to release inventory safety
    ticket_type = await get_ticket_type_for_update(db, reservation.ticket_type_id)

    if not ticket_type:
        raise NotFoundError(detail="Ticket type not found.")

    # * Mutate objects
    ticket_type.reserved_quantity -= reservation.quantity
    reservation.status = ReservationStatus.cancelled

    await save_changes(db, reservation)
    return reservation

from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationRead
from app.services.reservation import cancel_exsiting_reservation, create_new_reservation

router = APIRouter()


@router.post("", response_model=ReservationRead, status_code=status.HTTP_201_CREATED)
async def create_reservation_api(
    reservation_in: ReservationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-key")] = None,
) -> ReservationRead:
    """Create a new ticket reservation (locks inventory)."""
    reservation = await create_new_reservation(
        db, reservation_in, current_user.id, idempotency_key
    )
    return ReservationRead.model_validate(reservation)


@router.post("/{reservation_id}/cancel", response_model=ReservationRead)
async def cancel_reservation_api(
    reservation_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReservationRead:
    """Cancel a pending reservation and release tickets."""
    reservation = await cancel_exsiting_reservation(db, reservation_id, current_user.id)
    return ReservationRead.model_validate(reservation)

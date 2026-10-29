from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.circuit_breaker import CircuitBreakerError, payment_circuit_breaker
from app.core.dependencies import get_current_user
from app.core.settings import settings
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


@router.post("/{reservation_id}/checkout", status_code=status.HTTP_202_ACCEPTED)
async def checkout_reservation(
    reservation_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """Initialize payment for a reservation via the Mock Payment Provider."""

    # * Verify reservation exists and belongs to the user
    from app.repositories.reservation import get_reservation_by_id

    reservation = await get_reservation_by_id(db, reservation_id)
    if not reservation or reservation.user_id != current_user.id:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(detail="Reservation not found!")

    # * Call the Mock Payment Provider (Protected by Circuit Breaker!)
    payment_url = f"{settings.mock_payment.base_url}/process-payment"

    # * Define the async function to call
    async def call_provider() -> httpx.Response:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                payment_url, json={"reservation_id": reservation_id}
            )
            if response.status_code >= 500:
                response.raise_for_status()
            return response

    try:
        #! The Circuit Breaker's .call() method
        await payment_circuit_breaker.call(call_provider)
        return {"status": "Processing", "message": "Payment initiated with provider"}

    except CircuitBreakerError:
        # If the breaker is tripped, return 503 service unavailable
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment provider is currently unavailable. Please try again later.",
        )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to communicate with payment provider: {e}",
        )

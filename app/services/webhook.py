import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.reservation import ReservationStatus
from app.repositories.reservation import (
    get_reservation_by_id,
    get_ticket_type_for_update,
)
from app.repositories.webhook import create_webhook_event, get_webhook_by_provider_id
from app.schemas.webhook import WebhookPayload


async def process_payment_webhook(db: AsyncSession, payload: WebhookPayload) -> None:
    """Process the webhook with strict idempotency and pessimistic locking."""

    # * Idempotency Check: have we processed this webhook already???
    existing_event = await get_webhook_by_provider_id(db, payload.provider_event_id)
    if existing_event:
        # We already processed this! Return immediately without doing anything.
        # This prevents double-charging if the provider retries the webhook.
        return

    # * Fetch the reservation
    reservation = await get_reservation_by_id(db, payload.reservation_id)
    if not reservation:
        raise NotFoundError(detail="Reservation Not Found!")

    # ? Only process if the reservation is still pending
    if reservation.status != ReservationStatus.pending:
        return

    # * Move inventory: Lock the ticket type row!
    ticket_type = await get_ticket_type_for_update(db, reservation.ticket_type_id)
    if not ticket_type:
        raise NotFoundError(detail="Ticket Type Not Found!")

    # * Move tickets from "reserved" to "sold"
    ticket_type.reserved_quantity -= reservation.quantity
    ticket_type.sold_quantity += reservation.quantity

    # * Confirm the reservation
    reservation.status = ReservationStatus.confirmed

    # * Seve the webhook event to db(THIS COMMITS THE WHOLE TRANSACTION)
    await create_webhook_event(
        db, payload.provider_event_id, json.dumps(payload.model_dump())
    )

    # ? Trigger the Background email task via dramatiq!
    from app.core.tasks import (
        send_confirmation_email,  # Lazy import to break circular dependency
    )

    send_confirmation_email.send(reservation.id)

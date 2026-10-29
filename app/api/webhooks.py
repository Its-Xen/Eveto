from typing import Any

from fastapi import APIRouter, status

from app.core.tasks import process_webhook_event
from app.schemas.webhook import WebhookPayload

router = APIRouter()


@router.post("/payment", status_code=status.HTTP_200_OK)
async def receive_payment_webhook(payload: WebhookPayload) -> dict[str, Any]:
    """
    Endpoint for the Mock Payment Provider to call.
    Enqueues background processing.
    """
    # * Serialize the payload to JSON and pass it to the actor
    process_webhook_event.send(payload.model_dump_json())
    return {"status": "processed"}

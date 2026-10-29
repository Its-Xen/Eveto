import asyncio
import uuid

import httpx
from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

app = FastAPI(title="Mock Payment Provider")


# * The URL of Main Eveto API webhook endpoint
EVETO_WEBHOOK_URL = "http://localhost:8000/api/v1/webhooks/payment"


class PaymentRequest(BaseModel):
    reservation_id: int


@app.post("/process-payment")
async def process_payment(payload: PaymentRequest, background_tasks: BackgroundTasks):
    """
    Receives a payment request, instantly returns 202 Accepted,
    and processes the payment in the background before calling the webhook.
    """
    print(
        f"[MockPayment] Received payment request for reservation"
        f"{payload.reservation_id}"
    )

    # * Process the payment asynchronously (simulating a slow gateway)
    background_tasks.add_task(simulate_payment_and_call_webhook, payload.reservation_id)

    return {"status": "accepted", "message": "Payment is processing."}


async def simulate_payment_and_call_webhook(reservation_id: int):
    # ? Simulate network/processing delay(2 sec)
    await asyncio.sleep(2)

    # ? Generate unique provider ID
    #! THIS IS CRUCIAL: This ID guarantees idempotency.
    #! If the webhook is delivered twice,
    #! Eveto can use this ID to ensure it doesn't double-charge the user.
    provider_event_id = str(uuid.uuid4())

    # ? Prepare the webhook payload
    webhook_payload = {
        "provider_event_id": provider_event_id,
        "reservation_id": reservation_id,
        "status": "paid",
    }

    # ? Send the webhook to Eveto
    async with httpx.AsyncClient() as client:
        try:
            print(
                f"[MockPayment] Calling Eveto webhook for reservation"
                f"{reservation_id}..."
            )
            resp = await client.post(EVETO_WEBHOOK_URL, json=webhook_payload)
            print(
                f"[MockPayment] Webhook delivered! Eveto responded with "
                f"{resp.status_code}-{resp.text}"
            )
        except Exception as e:
            print(f"[MockPayment] Webhook call failed: {e}")

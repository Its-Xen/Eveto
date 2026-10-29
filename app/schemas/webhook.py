from pydantic import BaseModel


class WebhookPayload(BaseModel):
    provider_event_id: str
    reservation_id: int
    status: str  # "paid", "failed", ...

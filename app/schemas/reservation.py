from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.reservation import ReservationStatus


class ReservationCreate(BaseModel):
    ticket_type_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=10)  # Max 10 tickets per request


class ReservationRead(BaseModel):
    id: int
    user_id: int
    ticket_type_id: int
    quantity: int
    status: ReservationStatus
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

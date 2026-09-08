from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TicketTypeBase(BaseModel):
    event_id: int = Field(gt=0, examples=[1])
    name: str = Field(min_length=1, max_length=255, examples=["VIP Pass"])
    price_cents: int = Field(gt=0, examples=[50000])
    currency: str = Field(min_length=3, max_length=3, examples=["USD"])
    total_quantity: int = Field(gt=0, examples=[100])
    sales_start_at: datetime
    sales_end_at: datetime


class TicketTypeCreate(TicketTypeBase):
    pass


class TicketTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    price_cents: int | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    total_quantity: int | None = Field(default=None, gt=0)
    sales_start_at: datetime | None = None
    sales_end_at: datetime | None = None


class TicketTypeRead(TicketTypeBase):
    id: int
    reserved_quantity: int
    sold_quantity: int

    model_config = ConfigDict(from_attributes=True)

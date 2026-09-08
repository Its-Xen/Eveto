from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.event import StatusEnum


class EventBase(BaseModel):
    venue_id: int = Field(gt=0, examples=[1])
    title: str = Field(min_length=1, max_length=255, examples=["Summer Music Festival"])
    description: str = Field(
        min_length=1, max_length=1000, examples=["A great outdoor event"]
    )
    starts_at: datetime = Field(examples=["2024-12-31T20:00:00Z"])
    ends_at: datetime = Field(examples=["2025-01-01T01:00:00Z"])


class EventCreate(EventBase):
    status: StatusEnum = Field(default=StatusEnum.draft, examples=["draft"])


class EventUpdate(BaseModel):
    venue_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=1000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: StatusEnum | None = None


class EventRead(EventBase):
    id: int
    status: StatusEnum
    created_by_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

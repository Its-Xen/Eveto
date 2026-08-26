from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ticket_type import TicketType
    from app.models.user import User
    from app.models.venue import Venue


class StatusEnum(PyEnum):
    draft = "draft"
    published = "published"
    cancelled = "cancelled"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)

    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"))
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(1000))

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now
    )

    status: Mapped[StatusEnum] = mapped_column(
        Enum(StatusEnum, name="event_status"), default=StatusEnum.draft
    )

    # relationships
    venue: Mapped["Venue"] = relationship(back_populates="events_created")
    creator: Mapped["User"] = relationship(back_populates="events_created")
    tickets_created: Mapped[list["TicketType"]] = relationship(back_populates="event")

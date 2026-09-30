from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ticket_type import TicketType
    from app.models.user import User


class ReservationStatus(PyEnum):
    pending = "pending"
    confirmed = "confirmed"
    expired = "expired"
    cancelled = "cancelled"


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ticket_type_id: Mapped[int] = mapped_column(ForeignKey("tickettypes.id"))

    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status"),
        default=ReservationStatus.pending,
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now
    )

    # relationships
    creator: Mapped["User"] = relationship(back_populates="reservations_created")
    tickets_created: Mapped["TicketType"] = relationship(
        back_populates="reservations_created"
    )

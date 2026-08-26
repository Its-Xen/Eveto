from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.event import Event


class TicketType(Base):
    __tablename__ = "tickettypes"

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    name: Mapped[str] = mapped_column(String(255))
    price_cents: Mapped[int] = mapped_column()
    currency: Mapped[str] = mapped_column(String(10))
    total_quantity: Mapped[int] = mapped_column()
    reserved_quantity: Mapped[int] = mapped_column(default=0)
    sold_quantity: Mapped[int] = mapped_column(default=0)

    sales_start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now
    )
    sales_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # relationships
    event: Mapped["Event"] = relationship(back_populates="tickets_created")

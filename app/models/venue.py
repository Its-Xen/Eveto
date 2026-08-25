from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# This block ONLY runs when VS Code (or Mypy) is checking types.
# It prevents the circular import error
if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.user import User


class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(500))
    city: Mapped[str] = mapped_column(String(255))
    capacity: Mapped[int] = mapped_column()

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # * We use a string "User" to avoid circular import issues!
    # relationships
    creator: Mapped["User"] = relationship(back_populates="venues_created")
    events_created: Mapped[list["Event"]] = relationship(back_populates="venue")

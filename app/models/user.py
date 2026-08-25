from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# This block ONLY runs when VS Code (or Mypy) is checking types.
# It prevents the circular import error
if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.venue import Venue


class UserRole(PyEnum):
    customer = "customer"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100))

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.customer
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.now, timezone=True
    )  # * timezone=True tells Postgres to use TIMESTAMPTZ

    # relationships
    venues_created: Mapped[list["Venue"]] = relationship(back_populates="creator")
    events_created: Mapped[list["Event"]] = relationship(back_populates="creator")

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WebhookEvent(Base):
    __tablename__ = "webhookevents"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider_event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    payload: Mapped[str] = mapped_column(Text)  # * Store the raw JSON payload
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now
    )

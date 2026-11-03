from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ApiKey(Base):
    __tablename__ = "apikeys"

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_name: Mapped[str] = mapped_column(String(255))
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    rate_limit_tier: Mapped[int] = mapped_column(
        Integer, default=10
    )  # 10 requests per minute
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now
    )

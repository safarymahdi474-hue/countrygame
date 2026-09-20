from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.engine import Base


class WorldStatus(str, enum.Enum):
    UPCOMING = "upcoming"   # هنوز شروع نشده، در حال پر شدن
    ACTIVE = "active"       # در حال بازی
    ENDED = "ended"         # فصل تموم شده، فقط آرشیوه


class World(Base):
    """
    یک دنیای بازی مستقل (مثل World 1، World 2 ...).
    هر world مجموعه‌ی کاملاً جدا از کشورهاست — کشور یک بازیکن تو world A
    هیچ ربطی به کشورش تو world B نداره.
    """

    __tablename__ = "worlds"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[WorldStatus] = mapped_column(
        Enum(WorldStatus, native_enum=False), default=WorldStatus.UPCOMING
    )

    max_countries: Mapped[int] = mapped_column(default=48)
    season_length_days: Mapped[int] = mapped_column(default=45)

    started_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ends_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    countries: Mapped[list["Country"]] = relationship(back_populates="world")

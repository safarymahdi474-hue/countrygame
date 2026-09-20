from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.engine import Base


class WorldEventType(str, enum.Enum):
    DROUGHT = "drought"              # خشکسالی — تولید غذا کم می‌شه
    TRADE_BOOM = "trade_boom"        # رونق تجاری — کارمزد بازار صفر می‌شه
    ENERGY_CRISIS = "energy_crisis"  # بحران انرژی — تولید برق کم می‌شه
    STEEL_SHORTAGE = "steel_shortage"  # کمبود فولاد — تولید فولاد کم می‌شه
    OIL_BOOM = "oil_boom"            # رونق نفتی — تولید نفت زیاد می‌شه
    BUMPER_HARVEST = "bumper_harvest"  # برداشت پرمحصول — تولید غذا زیاد می‌شه


class WorldEvent(Base):
    """
    یه رویداد فعال (یا قبلاً فعال) روی یه دنیای بازی. هر لحظه حداکثر
    یه رویداد فعال داریم — رویداد قبلی قبل از شروع بعدی «تموم‌شده» علامت
    می‌خوره (ends_at گذشته).
    """

    __tablename__ = "world_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[WorldEventType] = mapped_column(Enum(WorldEventType, native_enum=False))

    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ends_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))

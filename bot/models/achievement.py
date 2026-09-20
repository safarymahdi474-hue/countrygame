from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.engine import Base


class Achievement(Base):
    """
    یه دستاوردِ ثبت‌شده برای یه کشور (مثلاً قهرمانیِ یه فصل). آرشیوه —
    حتی بعد از بسته‌شدنِ دنیا هم می‌مونه تا پروفایلِ تاریخیِ بازیکن حفظ بشه.
    """

    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(String(255))

    awarded_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

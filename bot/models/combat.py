from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.engine import Base


class CombatReport(Base):
    """
    آرشیو یک نبرد. جزئیات ریز تلفات هر نوع یگان به‌صورت JSON ساده
    (رشته‌ی متنی خلاصه) ذخیره می‌شه تا نیاز به جدول جدا نداشته باشیم؛
    اگه بعداً نیاز به کوئری روی تلفات تک‌تک یگان‌ها بود، جدول جدا اضافه می‌شه.
    """

    __tablename__ = "combat_reports"

    id: Mapped[int] = mapped_column(primary_key=True)

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    attacker_country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"), index=True
    )
    defender_country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"), index=True
    )

    category: Mapped[str] = mapped_column(String(16))  # ground/air/naval/missile
    winner: Mapped[str] = mapped_column(String(16))     # "attacker" یا "defender"

    attacker_power: Mapped[Numeric] = mapped_column(Numeric(14, 2))
    defender_power: Mapped[Numeric] = mapped_column(Numeric(14, 2))

    attacker_losses_summary: Mapped[str] = mapped_column(String(512))
    defender_losses_summary: Mapped[str] = mapped_column(String(512))

    money_looted: Mapped[Numeric] = mapped_column(Numeric(18, 2), default=0)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

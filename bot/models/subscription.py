from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.engine import Base


class SubscriptionTier(str, enum.Enum):
    NONE = "none"
    VIP = "vip"


class CountrySubscription(Base):
    """
    وضعیت اشتراک یک کشور. طراحی خودمون، متفاوت از منبع الهام:
    به‌جای اسم‌های خاص، فقط یک سطح VIP داریم که با گذشت expires_at خودکار
    غیرفعال محسوب می‌شه (نیازی به job پاک‌سازی نیست، فقط چک تاریخ کافیه).
    """

    __tablename__ = "country_subscriptions"

    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"), primary_key=True
    )
    tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, native_enum=False), default=SubscriptionTier.NONE
    )
    expires_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

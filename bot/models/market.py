from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.engine import Base
from bot.models.resources import ResourceType


class ListingStatus(str, enum.Enum):
    OPEN = "open"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MarketListing(Base):
    """
    یک آگهی در بازار جهانی: «X مقدار از کالای A رو می‌دم، Y مقدار از کالای B می‌خوام».
    resource_type = None یعنی اون طرف معامله پوله.

    ساده‌سازی نسبت به بازی‌های مشابه: فعلاً فاصله/مسیر حمل و نقل رو مدل نمی‌کنیم —
    معامله فوری انجام می‌شه اگه مرز تجاری هر دو طرف باز باشه. منطق مسیر و
    هزینه‌ی حمل رو می‌شه فاز جداگانه (لجستیک) بعداً اضافه کرد.
    """

    __tablename__ = "market_listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    seller_country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"), index=True
    )
    buyer_country_id: Mapped[int | None] = mapped_column(
        ForeignKey("countries.id", ondelete="SET NULL"), nullable=True
    )

    offer_resource: Mapped[ResourceType | None] = mapped_column(
        Enum(ResourceType, native_enum=False), nullable=True
    )
    offer_amount: Mapped[Numeric] = mapped_column(Numeric(18, 2))

    request_resource: Mapped[ResourceType | None] = mapped_column(
        Enum(ResourceType, native_enum=False), nullable=True
    )
    request_amount: Mapped[Numeric] = mapped_column(Numeric(18, 2))

    status: Mapped[ListingStatus] = mapped_column(
        Enum(ListingStatus, native_enum=False), default=ListingStatus.OPEN
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

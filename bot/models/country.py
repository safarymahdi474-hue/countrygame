from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.engine import Base


class CountryTier(str, enum.Enum):
    """
    سطح شروع کشور. عمداً اسم‌ها و مقادیر رو متفاوت از اپ منبعِ الهام
    طراحی می‌کنیم — فرمول دقیق مزایای هر تیر تو فاز اقتصاد مشخص می‌شه.
    """
    STANDARD = "standard"
    ADVANCED = "advanced"
    ELITE = "elite"


class Country(Base):
    """
    یک کشور متعلق به یک بازیکن، داخل یک world مشخص.
    قانون «یک اکانت تلگرام، یک کشور در هر world» با
    UniqueConstraint(owner_id, world_id) تضمین می‌شه.
    """

    __tablename__ = "countries"
    __table_args__ = (
        UniqueConstraint("owner_id", "world_id", name="uq_owner_per_world"),
        UniqueConstraint("nation_code", "world_id", name="uq_nation_per_world"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    world: Mapped["World"] = relationship(back_populates="countries")

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    owner: Mapped["User"] = relationship(back_populates="countries")

    # کد کشور واقعی (مثلاً "IT" برای ایتالیا) که بازیکن انتخاب کرده
    nation_code: Mapped[str] = mapped_column(String(4))
    display_name: Mapped[str] = mapped_column(String(64))

    tier: Mapped[CountryTier] = mapped_column(
        Enum(CountryTier, native_enum=False), default=CountryTier.STANDARD
    )

    # خزانه‌داری — Numeric به‌جای float تا خطای گرد کردن نداشته باشیم
    treasury: Mapped[Numeric] = mapped_column(Numeric(18, 2), default=0)

    # امتیازهای کش‌شده‌ی هر دسته (برای رتبه‌بندی سریع، بدون محاسبه هر بار)
    # مقدار واقعی‌شون تو سرویس‌های فاز بعد محاسبه و به‌روزرسانی می‌شه
    score_economic: Mapped[Numeric] = mapped_column(Numeric(12, 2), default=0)
    score_military: Mapped[Numeric] = mapped_column(Numeric(12, 2), default=0)
    score_territory: Mapped[Numeric] = mapped_column(Numeric(12, 2), default=0)
    score_development: Mapped[Numeric] = mapped_column(Numeric(12, 2), default=0)
    score_diplomacy: Mapped[Numeric] = mapped_column(Numeric(12, 2), default=0)

    # اگه اشغالِ کشورِ دیگه‌ای شده باشه، اینجا مشخصه؛ occupied_until گذشته
    # باشه یعنی خودکار آزاد شده (سرویس occupation این رو چک می‌کنه)
    occupied_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("countries.id", ondelete="SET NULL"), nullable=True
    )
    occupied_until: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_active_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

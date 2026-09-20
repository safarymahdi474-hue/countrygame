from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.engine import Base


class User(Base):
    """
    یک کاربر تلگرامی. طبق قانون «یک نفر، یک اکانت» هر user_id تلگرام
    فقط می‌تونه یک بار در هر world کشور داشته باشه — این محدودیت رو
    روی سطح Country (unique constraint) پیاده می‌کنیم، نه اینجا،
    چون یک کاربر ممکنه تو چند world مختلف بازی کنه.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language_code: Mapped[str] = mapped_column(String(8), default="fa")

    # آخرین دنیایی که کاربر توش فعال بوده — برای اینکه هندلرها بدونن
    # منظورش از «کشور من» تو کدوم دنیاست، وقتی کاربر تو چند دنیا کشور داره.
    current_world_id: Mapped[int | None] = mapped_column(
        ForeignKey("worlds.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    is_banned: Mapped[bool] = mapped_column(default=False)
    ban_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    countries: Mapped[list["Country"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )

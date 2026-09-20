from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.engine import Base


class BorderStatus(str, enum.Enum):
    CLOSED = "closed"
    LIMITED = "limited"
    OPEN = "open"


class CountryBorderPolicy(Base):
    """
    سیاست مرزی هر کشور. طبق طراحی خودمون (نه عین منبع الهام):
    مرزهای نظامی پیش‌فرض بسته‌ان (امنیت اول)، مرز تجاری پیش‌فرض بازه
    (بدون تجارت، اقتصاد از روز اول فلجه).
    """

    __tablename__ = "country_border_policies"

    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"), primary_key=True
    )
    ground_status: Mapped[BorderStatus] = mapped_column(
        Enum(BorderStatus, native_enum=False), default=BorderStatus.CLOSED
    )
    air_status: Mapped[BorderStatus] = mapped_column(
        Enum(BorderStatus, native_enum=False), default=BorderStatus.CLOSED
    )
    naval_status: Mapped[BorderStatus] = mapped_column(
        Enum(BorderStatus, native_enum=False), default=BorderStatus.CLOSED
    )
    trade_status: Mapped[BorderStatus] = mapped_column(
        Enum(BorderStatus, native_enum=False), default=BorderStatus.OPEN
    )


class TreatyType(str, enum.Enum):
    NON_AGGRESSION = "non_aggression"
    ALLIANCE = "alliance"


class TreatyStatus(str, enum.Enum):
    PENDING = "pending"    # پیشنهاد داده شده، منتظر پاسخ طرف مقابله
    ACTIVE = "active"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Treaty(Base):
    """
    پیمان دوطرفه بین دو کشور. جریان کار:
    یکی پیشنهاد می‌ده (PENDING) → طرف مقابل قبول (ACTIVE) یا رد (REJECTED) می‌کنه
    → هر دو طرف هر وقت بخوان می‌تونن لغوش کنن (CANCELLED).
    """

    __tablename__ = "treaties"
    __table_args__ = (
        UniqueConstraint(
            "world_id", "country_a_id", "country_b_id", "treaty_type",
            name="uq_treaty_pair_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))

    country_a_id: Mapped[int] = mapped_column(ForeignKey("countries.id", ondelete="CASCADE"))
    country_b_id: Mapped[int] = mapped_column(ForeignKey("countries.id", ondelete="CASCADE"))
    proposed_by_id: Mapped[int] = mapped_column(ForeignKey("countries.id", ondelete="CASCADE"))

    treaty_type: Mapped[TreatyType] = mapped_column(Enum(TreatyType, native_enum=False))
    status: Mapped[TreatyStatus] = mapped_column(
        Enum(TreatyStatus, native_enum=False), default=TreatyStatus.PENDING
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    responded_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Statement(Base):
    """یک بیانیه‌ی رسمی از یک کشور که بقیه می‌تونن ازش حمایت/محکومش کنن."""

    __tablename__ = "statements"

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    author_country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(128))
    body: Mapped[str] = mapped_column(Text)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StatementReactionType(str, enum.Enum):
    SUPPORT = "support"
    CONDEMN = "condemn"


class StatementReaction(Base):
    """هر کشور فقط یک واکنش (حمایت یا محکومیت) به هر بیانیه می‌تونه بده."""

    __tablename__ = "statement_reactions"
    __table_args__ = (
        UniqueConstraint("statement_id", "country_id", name="uq_reaction_per_country"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    statement_id: Mapped[int] = mapped_column(
        ForeignKey("statements.id", ondelete="CASCADE"), index=True
    )
    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"), index=True
    )
    reaction: Mapped[StatementReactionType] = mapped_column(
        Enum(StatementReactionType, native_enum=False)
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

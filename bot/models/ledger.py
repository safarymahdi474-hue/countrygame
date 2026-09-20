from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.engine import Base


class LedgerItem(str, enum.Enum):
    """چه چیزی جابه‌جا شده — پول یا یکی از منابع."""
    MONEY = "money"
    STEEL = "steel"
    OIL = "oil"
    URANIUM = "uranium"
    FOOD = "food"


class LedgerEntry(Base):
    """
    هر تغییر موجودیِ قابل‌توجه (پول یا منبع) از اینجا ثبت می‌شه — دفتر کل.
    delta مثبت = درآمد، منفی = هزینه. source یه برچسبِ کوتاهه (مثل
    "production:steel_mine" یا "market:sale") که بعداً می‌شه بر اساسش
    فیلتر/گروه‌بندی کرد.
    """

    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="CASCADE"), index=True
    )
    item: Mapped[LedgerItem] = mapped_column(Enum(LedgerItem, native_enum=False))
    delta: Mapped[Numeric] = mapped_column(Numeric(18, 2))
    source: Mapped[str] = mapped_column(String(64))

    occurred_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

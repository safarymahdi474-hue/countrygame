from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.ledger import LedgerEntry, LedgerItem
from bot.models.resources import ResourceType


def _item_from_resource(resource: ResourceType | None) -> LedgerItem | None:
    if resource is None:
        return LedgerItem.MONEY
    if resource == ResourceType.POWER:
        return None  # برق تو دفتر کل ثبت نمی‌شه — ذخیره نمی‌شه، بی‌معنیه
    return LedgerItem(resource.value)


async def record_entry(
    session: AsyncSession,
    *,
    country_id: int,
    item: ResourceType | None,
    delta: Decimal,
    source: str,
) -> None:
    if delta == 0:
        return
    ledger_item = _item_from_resource(item)
    if ledger_item is None:
        return
    session.add(LedgerEntry(
        country_id=country_id,
        item=ledger_item,
        delta=delta,
        source=source,
    ))


async def summary_since(
    session: AsyncSession, country_id: int, *, since: dt.datetime
) -> dict[LedgerItem, dict[str, Decimal]]:
    """
    برمی‌گردونه: {item: {"income": X, "expense": Y, "net": X-Y}}
    برای همه‌ی آیتم‌هایی که تراکنش داشتن، از since به بعد.
    """
    result = await session.execute(
        select(LedgerEntry).where(
            LedgerEntry.country_id == country_id, LedgerEntry.occurred_at >= since
        )
    )
    totals: dict[LedgerItem, dict[str, Decimal]] = {}
    for entry in result.scalars().all():
        bucket = totals.setdefault(
            entry.item, {"income": Decimal("0"), "expense": Decimal("0"), "net": Decimal("0")}
        )
        if entry.delta >= 0:
            bucket["income"] += entry.delta
        else:
            bucket["expense"] += -entry.delta
        bucket["net"] += entry.delta
    return totals


async def recent_entries(
    session: AsyncSession, country_id: int, *, limit: int = 20
) -> list[LedgerEntry]:
    result = await session.execute(
        select(LedgerEntry)
        .where(LedgerEntry.country_id == country_id)
        .order_by(LedgerEntry.occurred_at.desc(), LedgerEntry.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())

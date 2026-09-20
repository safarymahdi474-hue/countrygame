"""
لایه‌ی مشترک برای خوندن/تغییر موجودی — چه پول باشه چه یه نوع منبع.
هر جای دیگه‌ی پروژه (بازار، ساخت واحد، ...) به‌جای دستکاری مستقیم
Country.treasury یا CountryResource، از این توابع استفاده می‌کنه تا
منطق «کافی بودن موجودی» یک‌جا و یک‌شکل بمونه.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.country import Country
from bot.models.resources import CountryResource, ResourceType
from bot.services import ledger


class InsufficientFundsError(Exception):
    pass


async def get_balance(
    session: AsyncSession, country_id: int, item: ResourceType | None
) -> Decimal:
    """item=None یعنی پول (treasury)."""
    if item is None:
        result = await session.execute(select(Country.treasury).where(Country.id == country_id))
        return result.scalar_one()

    result = await session.execute(
        select(CountryResource.amount).where(
            CountryResource.country_id == country_id,
            CountryResource.resource_type == item,
        )
    )
    amount = result.scalar_one_or_none()
    return amount or Decimal("0")


async def adjust_balance(
    session: AsyncSession,
    country_id: int,
    item: ResourceType | None,
    delta: Decimal,
    *,
    source: str = "other",
) -> None:
    """
    delta مثبت = افزایش، منفی = کاهش. اگه کاهش باعث منفی شدن موجودی بشه
    InsufficientFundsError پرتاب می‌شه و هیچ تغییری اعمال نمی‌شه.

    `source` یه برچسب کوتاهه (مثل "market:sale"، "upkeep:tank") که تو
    دفتر کل (bot.services.ledger) ثبت می‌شه؛ پیش‌فرض "other" برای
    جاهایی که هنوز دقیق برچسب‌گذاری نشدن.
    """
    if item is None:
        result = await session.execute(select(Country).where(Country.id == country_id))
        country = result.scalar_one()
        new_amount = country.treasury + delta
        if new_amount < 0:
            raise InsufficientFundsError("موجودی پول کافی نیست.")
        country.treasury = new_amount
        await ledger.record_entry(session, country_id=country_id, item=item, delta=delta, source=source)
        return

    result = await session.execute(
        select(CountryResource).where(
            CountryResource.country_id == country_id,
            CountryResource.resource_type == item,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        if delta < 0:
            raise InsufficientFundsError(f"موجودی {item.value} کافی نیست.")
        row = CountryResource(country_id=country_id, resource_type=item, amount=delta)
        session.add(row)
        await ledger.record_entry(session, country_id=country_id, item=item, delta=delta, source=source)
        return

    new_amount = row.amount + delta
    if new_amount < 0:
        raise InsufficientFundsError(f"موجودی {item.value} کافی نیست.")
    row.amount = new_amount
    await ledger.record_entry(session, country_id=country_id, item=item, delta=delta, source=source)

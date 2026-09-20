"""
اشغال کشور — طراحی خودمون: وقتی حمله‌کننده با اختلاف قدرت خیلی زیاد
(margin بالای یه آستانه) برنده بشه، می‌تونه به‌جای فقط غارت، کشور
مدافع رو برای یه مدت مشخص اشغال کنه. تا وقتی اشغاله:
- تولید منابعِ مدافع نصف می‌شه (جریمه‌ی اقتصادی)
- امتیاز قلمرو (territory) اشغال‌کننده بالا می‌ره

اشغال خودکار بعد از OCCUPATION_DURATION_DAYS تموم می‌شه — بدون نیاز به
اقدام دستی؛ liberate_expired_occupations همون‌جوری که فصل‌های منقضی رو
می‌بنده، این رو هم پاک می‌کنه.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.country import Country

OCCUPATION_MARGIN_THRESHOLD = Decimal("0.6")  # حداقل اختلاف نسبیِ قدرت برای امکان اشغال
OCCUPATION_DURATION_DAYS = 3
PRODUCTION_PENALTY_WHILE_OCCUPIED = Decimal("0.5")  # نصف تولید


class OccupationError(Exception):
    pass


def can_occupy(attacker_power: Decimal, defender_power: Decimal) -> bool:
    total = attacker_power + defender_power
    if total <= 0:
        return False
    margin = (attacker_power - defender_power) / total
    return margin >= OCCUPATION_MARGIN_THRESHOLD


async def occupy_country(
    session: AsyncSession, *, occupier_country_id: int, target_country_id: int
) -> Country:
    if occupier_country_id == target_country_id:
        raise OccupationError("نمی‌تونی خودت رو اشغال کنی.")

    target = await session.get(Country, target_country_id)
    if target is None:
        raise OccupationError("کشور مدافع پیدا نشد.")

    now = dt.datetime.now(dt.timezone.utc)
    if target.occupied_by_id is not None and target.occupied_until and target.occupied_until > now:
        if target.occupied_by_id != occupier_country_id:
            raise OccupationError("این کشور از قبل توسط کشور دیگه‌ای اشغال شده.")

    target.occupied_by_id = occupier_country_id
    target.occupied_until = now + dt.timedelta(days=OCCUPATION_DURATION_DAYS)
    return target


async def is_occupied(session: AsyncSession, country_id: int) -> bool:
    country = await session.get(Country, country_id)
    if country is None or country.occupied_by_id is None or country.occupied_until is None:
        return False
    occupied_until = country.occupied_until
    if occupied_until.tzinfo is None:
        occupied_until = occupied_until.replace(tzinfo=dt.timezone.utc)
    return occupied_until > dt.datetime.now(dt.timezone.utc)


async def count_occupied_by(session: AsyncSession, occupier_country_id: int) -> int:
    now = dt.datetime.now(dt.timezone.utc)
    result = await session.execute(
        select(Country).where(
            Country.occupied_by_id == occupier_country_id,
            Country.occupied_until.is_not(None),
        )
    )
    count = 0
    for c in result.scalars().all():
        occupied_until = c.occupied_until
        if occupied_until.tzinfo is None:
            occupied_until = occupied_until.replace(tzinfo=dt.timezone.utc)
        if occupied_until > now:
            count += 1
    return count


async def liberate_expired_occupations(session: AsyncSession) -> list[Country]:
    now = dt.datetime.now(dt.timezone.utc)
    result = await session.execute(
        select(Country).where(
            Country.occupied_by_id.is_not(None),
            Country.occupied_until.is_not(None),
        )
    )
    liberated: list[Country] = []
    for country in result.scalars().all():
        occupied_until = country.occupied_until
        if occupied_until.tzinfo is None:
            occupied_until = occupied_until.replace(tzinfo=dt.timezone.utc)
        if occupied_until <= now:
            country.occupied_by_id = None
            country.occupied_until = None
            liberated.append(country)
    return liberated

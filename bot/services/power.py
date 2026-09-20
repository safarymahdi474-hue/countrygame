"""
تراز برق: تولید (نیروگاه‌ها) در برابر مصرف (بقیه‌ی ساختمان‌ها). مدل ساده‌ست —
هر ساختمان (به‌جز نیروگاه) یه مصرف ثابت داره که با ساختنش (سطح ۱) فعال
می‌شه؛ سطح بالاتر مصرف رو زیاد نمی‌کنه (فقط تولید منابع رو). این باعث
می‌شه ساخت زیرساخت جدید واقعاً به برق کافی نیاز داشته باشه، بدون اینکه
محاسبات پیچیده بشه.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.buildings import BUILDING_CATEGORY, BuildingCategory, CountryBuilding
from bot.models.country import Country
from bot.services.economy import BUILDING_ECONOMICS, daily_output
from bot.services.world_events import get_active_event, power_multiplier


async def compute_power_balance(session: AsyncSession, country_id: int) -> tuple[Decimal, Decimal]:
    """(produced, consumed) — هر دو بر حسب واحد برق در روز."""
    result = await session.execute(
        select(CountryBuilding).where(
            CountryBuilding.country_id == country_id, CountryBuilding.level > 0
        )
    )
    country_result = await session.execute(select(Country.world_id).where(Country.id == country_id))
    world_id = country_result.scalar_one_or_none()
    active_event = await get_active_event(session, world_id) if world_id is not None else None
    event_multiplier = power_multiplier(active_event)

    produced = Decimal("0")
    consumed = Decimal("0")
    for row in result.scalars().all():
        econ = BUILDING_ECONOMICS[row.building_type]
        if BUILDING_CATEGORY.get(row.building_type) == BuildingCategory.POWER:
            produced += daily_output(row.building_type, row.level) * event_multiplier
        else:
            consumed += Decimal(econ.power_consumption)
    return produced, consumed


async def available_power(session: AsyncSession, country_id: int) -> Decimal:
    produced, consumed = await compute_power_balance(session, country_id)
    return produced - consumed

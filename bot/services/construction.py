"""
نسخه‌ی MVP: ساخت/ارتقا فوریه (بدون تایمر واقعی). صف‌بندی و زمان واقعی
ساخت (که VIP سریع‌ترش می‌کنه) رو فاز جداگانه‌ی "صف ساخت‌وساز" اضافه
می‌کنیم؛ فعلاً فقط هزینه و منطق سطح رو درست پیاده می‌کنیم که پایه‌ی
همه‌چیز دیگه‌ست.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.buildings import BUILDING_CATEGORY, MAX_BUILDING_LEVEL, BuildingCategory, BuildingType, CountryBuilding
from bot.services.economy import BUILDING_ECONOMICS, upgrade_cost
from bot.services.power import compute_power_balance
from bot.services.wallet import InsufficientFundsError, adjust_balance


class ConstructionError(Exception):
    pass


async def _get_or_create_building(
    session: AsyncSession, country_id: int, building_type: BuildingType
) -> CountryBuilding:
    result = await session.execute(
        select(CountryBuilding).where(
            CountryBuilding.country_id == country_id,
            CountryBuilding.building_type == building_type,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = CountryBuilding(country_id=country_id, building_type=building_type, level=0)
        session.add(row)
        await session.flush()
    return row


async def upgrade_building(
    session: AsyncSession, country_id: int, building_type: BuildingType
) -> CountryBuilding:
    building = await _get_or_create_building(session, country_id, building_type)

    if building.level >= MAX_BUILDING_LEVEL:
        raise ConstructionError("این ساختمان به سقف سطح رسیده.")

    target_level = building.level + 1
    cost = upgrade_cost(building_type, target_level)

    # ساخت اولیه‌ی هر ساختمانِ غیرنیروگاهی یه مصرف برق ثابت اضافه می‌کنه —
    # اگه برق کافی نباشه، نمی‌ذاریم ساخته بشه (نیروگاه‌ها خودشون این محدودیت رو ندارن).
    if building.level == 0 and BUILDING_CATEGORY.get(building_type) != BuildingCategory.POWER:
        needed_power = Decimal(BUILDING_ECONOMICS[building_type].power_consumption)
        if needed_power > 0:
            produced, consumed = await compute_power_balance(session, country_id)
            if consumed + needed_power > produced:
                raise ConstructionError(
                    f"برق کافی نیست — {produced - consumed} در دسترس، {needed_power} لازمه. "
                    "اول یه نیروگاه بساز/ارتقا بده."
                )

    try:
        await adjust_balance(session, country_id, None, -cost, source=f"construction:{building_type.value}")
    except InsufficientFundsError:
        raise ConstructionError(f"پول کافی نیست — {cost} لازمه.") from None

    building.level = target_level
    return building

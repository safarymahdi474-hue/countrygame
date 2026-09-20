from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.buildings import BuildingType, CountryBuilding
from bot.models.country import Country
from bot.models.military import (
    UNIT_CAPACITY_BUILDING,
    UNIT_CATEGORY,
    UNIT_FACTORY,
    UNIT_STATS,
    CountryUnit,
    UnitCategory,
    UnitType,
)
from bot.models.resources import CountryResource, ResourceType
from bot.services.economy import capacity_at_level, lab_unit_cost_discount
from bot.services import ledger


class BuildUnitError(Exception):
    pass


async def _building_level(
    session: AsyncSession, country_id: int, building_type
) -> int:
    result = await session.execute(
        select(CountryBuilding.level).where(
            CountryBuilding.country_id == country_id,
            CountryBuilding.building_type == building_type,
        )
    )
    level = result.scalar_one_or_none()
    return level or 0


async def get_capacity(
    session: AsyncSession, country_id: int, category: UnitCategory
) -> tuple[int, int]:
    """(used, total) اسلات‌های اشغال‌شده و کل ظرفیت برای یک دسته‌ی نظامی."""
    building_type = {
        UnitCategory.GROUND: "garrison",
        UnitCategory.AIR: "airport",
        UnitCategory.NAVAL: "port",
        UnitCategory.MISSILE: "missile_silo",
    }
    from bot.models.buildings import BuildingType

    bt = BuildingType(building_type[category])
    level = await _building_level(session, country_id, bt)
    total = capacity_at_level(bt, level)

    result = await session.execute(
        select(CountryUnit).where(CountryUnit.country_id == country_id)
    )
    used = 0
    for unit in result.scalars().all():
        if UNIT_CATEGORY[unit.unit_type] == category:
            used += UNIT_STATS[unit.unit_type].capacity_slots * unit.quantity

    return used, total


async def build_units(
    session: AsyncSession, country_id: int, unit_type: UnitType, quantity: int
) -> None:
    """
    ساخت `quantity` عدد از یک یگان: چک ظرفیت، چک کارخانه، چک و کسر منابع/پول.
    در صورت هر مشکلی BuildUnitError پرتاب می‌شه و هیچ تغییری اعمال نمی‌شه
    (session باید بعداً commit/rollback بشه توسط caller — طبق الگوی session_scope).
    """
    if quantity <= 0:
        raise BuildUnitError("تعداد باید مثبت باشه.")

    stats = UNIT_STATS[unit_type]
    category = UNIT_CATEGORY[unit_type]

    # ۱. چک کارخانه (به‌جز پیاده‌نظام که فقط پادگان لازم داره)
    factory_type = UNIT_FACTORY[unit_type]
    factory_level = await _building_level(session, country_id, factory_type)
    if factory_level <= 0 and factory_type.value != "garrison":
        raise BuildUnitError("کارخانه‌ی لازم برای این یگان ساخته نشده.")

    # ۲. چک ظرفیت
    used, total = await get_capacity(session, country_id, category)
    needed_slots = stats.capacity_slots * quantity
    if used + needed_slots > total:
        raise BuildUnitError(
            f"ظرفیت کافی نیست: {used}/{total} اشغال شده، {needed_slots} اسلات لازمه."
        )

    # ۳. چک و کسر پول — با تخفیف احتمالیِ آزمایشگاه (LAB)
    result = await session.execute(select(Country).where(Country.id == country_id))
    country = result.scalar_one()

    lab_level_result = await session.execute(
        select(CountryBuilding.level).where(
            CountryBuilding.country_id == country_id,
            CountryBuilding.building_type == BuildingType.LAB,
        )
    )
    lab_level = lab_level_result.scalar_one_or_none() or 0
    discount = lab_unit_cost_discount(lab_level)

    total_cost_money = stats.build_cost_money * quantity * (Decimal("1") - discount)
    if country.treasury < total_cost_money:
        raise BuildUnitError("پول کافی نیست.")

    # ۴. چک و کسر منابع (تخفیفِ آزمایشگاه فقط رو پول اعمال می‌شه، نه منابع خام)
    resource_rows: dict[ResourceType, CountryResource] = {}
    for res_type, per_unit in stats.build_cost_resources.items():
        needed = per_unit * quantity
        row_result = await session.execute(
            select(CountryResource).where(
                CountryResource.country_id == country_id,
                CountryResource.resource_type == res_type,
            )
        )
        row = row_result.scalar_one_or_none()
        available = row.amount if row else Decimal("0")
        if available < needed:
            raise BuildUnitError(f"منبع {res_type.value} کافی نیست.")
        resource_rows[res_type] = row

    # همه‌چیز اوکیه — حالا واقعاً کم می‌کنیم
    country.treasury -= total_cost_money
    await ledger.record_entry(
        session, country_id=country_id, item=None, delta=-total_cost_money,
        source=f"unit_build:{unit_type.value}",
    )
    for res_type, per_unit in stats.build_cost_resources.items():
        spent = per_unit * quantity
        resource_rows[res_type].amount -= spent
        await ledger.record_entry(
            session, country_id=country_id, item=res_type, delta=-spent,
            source=f"unit_build:{unit_type.value}",
        )

    unit_result = await session.execute(
        select(CountryUnit).where(
            CountryUnit.country_id == country_id,
            CountryUnit.unit_type == unit_type,
        )
    )
    unit_row = unit_result.scalar_one_or_none()
    if unit_row is None:
        unit_row = CountryUnit(country_id=country_id, unit_type=unit_type, quantity=0)
        session.add(unit_row)
    unit_row.quantity += quantity


async def military_score(session: AsyncSession, country_id: int) -> Decimal:
    """
    امتیاز نظامی کل کشور — جمع (attack * quantity) با وزن یکسان بین دسته‌ها،
    به‌علاوه یک ریشه‌ی نرم‌کننده تا کمیت خام رو له نکنه (کیفیت هم مهم بمونه).
    فرمول دقیق‌تر (با بونس ستاد فرماندهی و ...) رو فاز نبرد کامل می‌کنیم.
    """
    result = await session.execute(
        select(CountryUnit).where(CountryUnit.country_id == country_id)
    )
    total = Decimal("0")
    for unit in result.scalars().all():
        stats = UNIT_STATS[unit.unit_type]
        total += Decimal(stats.attack) * Decimal(unit.quantity)
    return total

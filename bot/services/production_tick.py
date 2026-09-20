"""
موتور tick: یک‌بار برای یک کشور، تولید همه ساختمان‌هاش رو محاسبه
و به انبار منابعش اضافه می‌کنه. این تابع رو یک scheduler (فاز بعد)
هر چند دقیقه برای همه کشورهای فعال صدا می‌زنه.

توجه: تولیدِ لحظه‌به‌لحظه عمداً تو دفتر کل (bot.services.ledger) ثبت
نمی‌شه — چون هر تیک ممکنه هر چند ثانیه اجرا بشه و برای هر ساختمانِ هر
کشور یه ردیف جدا بسازه (رشد بی‌رویه‌ی جدول). دفتر کل برای تراکنش‌های
مجزا (معامله، غارت، ساخت یگان، نگهداری) کاربرد داره؛ تولید مستمر رو
می‌شه از روی خودِ موجودی انبار (CountryResource) دنبال کرد.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.buildings import BUILDING_OUTPUT_RESOURCE, CountryBuilding
from bot.models.country import Country
from bot.models.resources import CountryResource, ResourceType
from bot.services.economy import daily_output
from bot.services.occupation import PRODUCTION_PENALTY_WHILE_OCCUPIED, is_occupied
from bot.services.world_events import get_active_event, resource_multiplier


async def _get_or_create_resource(
    session: AsyncSession, country_id: int, resource_type: ResourceType
) -> CountryResource:
    result = await session.execute(
        select(CountryResource).where(
            CountryResource.country_id == country_id,
            CountryResource.resource_type == resource_type,
        )
    )
    resource = result.scalar_one_or_none()
    if resource is None:
        resource = CountryResource(
            country_id=country_id, resource_type=resource_type, amount=Decimal("0")
        )
        session.add(resource)
        await session.flush()
    return resource


async def run_production_tick(
    session: AsyncSession, country_id: int, *, elapsed_seconds: int
) -> dict[ResourceType, Decimal]:
    """
    تولید همه‌ی ساختمان‌های یک کشور رو برای بازه‌ی elapsed_seconds محاسبه
    و به انبارش اضافه می‌کنه. مقدار افزوده‌شده به هر منبع رو برمی‌گردونه
    (برای نمایش «+X در روز» به کاربر).
    """
    result = await session.execute(
        select(CountryBuilding).where(
            CountryBuilding.country_id == country_id,
            CountryBuilding.level > 0,
        )
    )
    buildings = result.scalars().all()

    fraction_of_day = Decimal(elapsed_seconds) / Decimal(86400)
    added: dict[ResourceType, Decimal] = {}

    penalty_multiplier = Decimal("1")
    if await is_occupied(session, country_id):
        penalty_multiplier = PRODUCTION_PENALTY_WHILE_OCCUPIED

    country_result = await session.execute(select(Country.world_id).where(Country.id == country_id))
    world_id = country_result.scalar_one_or_none()
    active_event = await get_active_event(session, world_id) if world_id is not None else None

    for building in buildings:
        output_resource = BUILDING_OUTPUT_RESOURCE.get(building.building_type)
        if output_resource is None:
            continue
        if output_resource == ResourceType.POWER:
            # برق ذخیره نمی‌شه — تراز لحظه‌ای تولید/مصرفش رو bot.services.power حساب می‌کنه
            continue

        per_day = daily_output(building.building_type, building.level)
        event_multiplier = resource_multiplier(active_event, output_resource)
        amount_this_tick = per_day * fraction_of_day * penalty_multiplier * event_multiplier
        if amount_this_tick <= 0:
            continue

        resource = await _get_or_create_resource(session, country_id, output_resource)
        new_amount = resource.amount + amount_this_tick
        if resource.capacity is not None:
            new_amount = min(new_amount, resource.capacity)
        resource.amount = new_amount

        added[output_resource] = added.get(output_resource, Decimal("0")) + amount_this_tick

    return added

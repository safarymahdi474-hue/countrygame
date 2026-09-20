"""
نگهداری روزانه‌ی یگان‌ها: هر یگان یه هزینه‌ی پولی و/یا منبعی داره که
باید مرتب پرداخت بشه، وگرنه ارتش داشتن هیچ هزینه‌ای نداره و تعادل بازی
به‌هم می‌خوره.

قانون این پروژه (متفاوت از خیلی بازی‌های مشابه): کمبود *پول* باعث بدهی
می‌شه (خزانه منفی می‌ره — واقع‌گرایانه‌تره و بازیکن رو مجبور به تصمیم
می‌کنه)، ولی کمبود *منبع فیزیکی* (نفت/غذا و ...) نمی‌تونه منفی بشه —
فقط تا صفر مصرف می‌شه؛ باقیِ نیاز رو (پیاده‌سازی فاز بعد) با افت آماده‌به‌کاری
یگان‌ها جبران می‌کنیم؛ فعلاً همون clamp به صفر کافیه.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.country import Country
from bot.models.military import UNIT_STATS, CountryUnit
from bot.models.resources import CountryResource, ResourceType
from bot.services import ledger


async def run_upkeep_tick(
    session: AsyncSession, country_id: int, *, elapsed_seconds: int
) -> dict[str, Decimal]:
    """
    نگهداری همه‌ی یگان‌های یک کشور رو برای بازه‌ی elapsed_seconds کسر می‌کنه.
    دیکشنری {"money": ..., resource.value: ...} از مقدار واقعاً کسرشده برمی‌گردونه.
    """
    fraction_of_day = Decimal(elapsed_seconds) / Decimal(86400)

    result = await session.execute(
        select(CountryUnit).where(CountryUnit.country_id == country_id, CountryUnit.quantity > 0)
    )
    units = result.scalars().all()

    total_money_due = Decimal("0")
    resource_due: dict[ResourceType, Decimal] = {}

    for unit in units:
        stats = UNIT_STATS[unit.unit_type]
        qty = Decimal(unit.quantity)
        total_money_due += stats.upkeep_money_per_day * qty * fraction_of_day
        for res_type, per_unit in stats.upkeep_resources_per_day.items():
            resource_due[res_type] = resource_due.get(res_type, Decimal("0")) + per_unit * qty * fraction_of_day

    spent: dict[str, Decimal] = {}

    if total_money_due > 0:
        country_result = await session.execute(select(Country).where(Country.id == country_id))
        country = country_result.scalar_one()
        country.treasury -= total_money_due  # می‌تونه منفی بشه — بدهی ملی
        spent["money"] = total_money_due
        await ledger.record_entry(
            session, country_id=country_id, item=None, delta=-total_money_due, source="upkeep:units"
        )

    for res_type, due in resource_due.items():
        if due <= 0:
            continue
        row_result = await session.execute(
            select(CountryResource).where(
                CountryResource.country_id == country_id,
                CountryResource.resource_type == res_type,
            )
        )
        row = row_result.scalar_one_or_none()
        available = row.amount if row else Decimal("0")
        actually_spent = min(available, due)
        if row is not None:
            row.amount -= actually_spent
        spent[res_type.value] = actually_spent
        await ledger.record_entry(
            session, country_id=country_id, item=res_type, delta=-actually_spent, source="upkeep:units"
        )

    return spent

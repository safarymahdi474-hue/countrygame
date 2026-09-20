"""
محاسبه‌ی امتیاز خام هر یک از پنج دسته برای یک کشور، و ذخیره‌ش روی
ستون‌های cache شده‌ی Country (score_economic و ...). این تابع رو
سرویس رتبه‌بندی (ranking.py) صدا می‌زنه، هم برای خود کشور هم برای
مقایسه با بقیه.

توجه: این فرمول‌ها placeholder منطقی‌ان و با رشد پروژه (وقتی قلمرو/اشغال
واقعی و اقتصاد مالی کامل اضافه شد) دقیق‌تر می‌شن؛ جایی که ساده‌سازی شده
تو کامنت مشخصه.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.buildings import BuildingCategory, CountryBuilding
from bot.models.country import Country
from bot.models.diplomacy import (
    StatementReaction,
    StatementReactionType,
    Statement,
    Treaty,
    TreatyStatus,
)
from bot.services.military import military_score
from bot.services.occupation import count_occupied_by


async def _sum_building_levels(
    session: AsyncSession, country_id: int, category: BuildingCategory
) -> int:
    from bot.models.buildings import BUILDING_CATEGORY

    result = await session.execute(
        select(CountryBuilding).where(CountryBuilding.country_id == country_id)
    )
    return sum(
        row.level for row in result.scalars().all()
        if BUILDING_CATEGORY.get(row.building_type) == category
    )


async def compute_economic_score(session: AsyncSession, country: Country) -> Decimal:
    """
    فعلاً: خزانه + وزنی از سطح ساختمان‌های منابع.
    وقتی بخش کامل «دفتر کل درآمد» (بانک/گردشگری/بیمه/...) اضافه شد،
    این تابع کامل‌تر می‌شه.
    """
    resource_building_levels = await _sum_building_levels(
        session, country.id, BuildingCategory.RESOURCE
    )
    return country.treasury + Decimal(resource_building_levels) * Decimal("50000")


async def compute_military_score(session: AsyncSession, country: Country) -> Decimal:
    return await military_score(session, country.id)


async def compute_territory_score(session: AsyncSession, country: Country) -> Decimal:
    """
    قلمرو = تعداد کشورهایی که الان اشغال کردی (وزن سنگین) + زیرساخت نظامی
    (پادگان/فرودگاه/بندر/سیلو) به‌عنوان نشونه‌ی توان گسترش.
    """
    occupied_count = await count_occupied_by(session, country.id)
    military_building_levels = await _sum_building_levels(
        session, country.id, BuildingCategory.MILITARY
    )
    return Decimal(occupied_count) * Decimal("50") + Decimal(military_building_levels)


async def compute_development_score(session: AsyncSession, country: Country) -> Decimal:
    welfare_levels = await _sum_building_levels(session, country.id, BuildingCategory.WELFARE)
    return Decimal(welfare_levels)


async def compute_diplomacy_score(session: AsyncSession, country: Country) -> Decimal:
    treaty_result = await session.execute(
        select(Treaty).where(
            (Treaty.country_a_id == country.id) | (Treaty.country_b_id == country.id),
            Treaty.status == TreatyStatus.ACTIVE,
        )
    )
    active_treaties = len(treaty_result.scalars().all())

    support_result = await session.execute(
        select(StatementReaction)
        .join(Statement, Statement.id == StatementReaction.statement_id)
        .where(
            Statement.author_country_id == country.id,
            StatementReaction.reaction == StatementReactionType.SUPPORT,
        )
    )
    support_count = len(support_result.scalars().all())

    return Decimal(active_treaties) * Decimal("5") + Decimal(support_count)


async def recompute_scores(session: AsyncSession, country_id: int) -> Country:
    """امتیاز هر پنج دسته رو دوباره حساب و روی خود Country ذخیره می‌کنه."""
    result = await session.execute(select(Country).where(Country.id == country_id))
    country = result.scalar_one()

    country.score_economic = await compute_economic_score(session, country)
    country.score_military = await compute_military_score(session, country)
    country.score_territory = await compute_territory_score(session, country)
    country.score_development = await compute_development_score(session, country)
    country.score_diplomacy = await compute_diplomacy_score(session, country)

    return country

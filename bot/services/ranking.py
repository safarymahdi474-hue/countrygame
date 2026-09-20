"""
رتبه‌بندی کلی: هر دسته نسبت به بهترین کشور همون دسته نرمال می‌شه
(تا یک عدد نجومی تو یک دسته، کل رتبه‌بندی رو مخدوش نکنه)، بعد با
وزن مخصوص خودش جمع می‌شه. وزن‌ها طراحی خودمونه (جمعاً ۱۰۰).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.country import Country

CATEGORY_WEIGHTS: dict[str, Decimal] = {
    "economic": Decimal("35"),
    "military": Decimal("25"),
    "territory": Decimal("15"),
    "development": Decimal("15"),
    "diplomacy": Decimal("10"),
}


@dataclass(frozen=True, slots=True)
class RankingEntry:
    country_id: int
    overall_score: Decimal
    breakdown: dict[str, Decimal]


async def compute_leaderboard(session: AsyncSession, world_id: int) -> list[RankingEntry]:
    result = await session.execute(select(Country).where(Country.world_id == world_id))
    countries = result.scalars().all()
    if not countries:
        return []

    raw_scores: dict[str, dict[int, Decimal]] = {cat: {} for cat in CATEGORY_WEIGHTS}
    for country in countries:
        raw_scores["economic"][country.id] = country.score_economic
        raw_scores["military"][country.id] = country.score_military
        raw_scores["territory"][country.id] = country.score_territory
        raw_scores["development"][country.id] = country.score_development
        raw_scores["diplomacy"][country.id] = country.score_diplomacy

    max_per_category = {
        cat: max(values.values(), default=Decimal("0")) for cat, values in raw_scores.items()
    }

    entries: list[RankingEntry] = []
    for country in countries:
        breakdown: dict[str, Decimal] = {}
        overall = Decimal("0")
        for cat, weight in CATEGORY_WEIGHTS.items():
            best = max_per_category[cat]
            own = raw_scores[cat][country.id]
            normalized = (own / best * weight) if best > 0 else Decimal("0")
            breakdown[cat] = normalized
            overall += normalized
        entries.append(RankingEntry(country_id=country.id, overall_score=overall, breakdown=breakdown))

    entries.sort(key=lambda e: e.overall_score, reverse=True)
    return entries

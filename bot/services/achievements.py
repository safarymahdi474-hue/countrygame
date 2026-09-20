from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.achievement import Achievement
from bot.models.country import Country
from bot.services import ranking, scoring


async def award_season_champion(session: AsyncSession, world_id: int) -> Country | None:
    """
    قبل از بسته‌شدنِ یه دنیا صدا زده می‌شه: امتیاز همه رو تازه می‌کنه،
    رتبه‌بندی نهایی رو حساب می‌کنه، و به نفر اول یه دستاورد می‌ده.
    اگه دنیا کلاً کشوری نداشته باشه، None برمی‌گردونه.
    """
    result = await session.execute(select(Country.id).where(Country.world_id == world_id))
    country_ids = [row[0] for row in result.all()]
    for country_id in country_ids:
        await scoring.recompute_scores(session, country_id)

    leaderboard = await ranking.compute_leaderboard(session, world_id)
    if not leaderboard:
        return None

    champion_id = leaderboard[0].country_id
    champion = await session.get(Country, champion_id)

    session.add(Achievement(
        world_id=world_id,
        country_id=champion_id,
        title="🏆 قهرمان فصل",
        description=f"رتبه‌ی اول در پایان فصل با امتیاز کلی {leaderboard[0].overall_score:,.1f}",
    ))

    return champion


async def list_achievements(session: AsyncSession, country_id: int) -> list[Achievement]:
    result = await session.execute(
        select(Achievement)
        .where(Achievement.country_id == country_id)
        .order_by(Achievement.awarded_at.desc())
    )
    return list(result.scalars().all())

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.world import World, WorldStatus
from bot.services import achievements


class SeasonError(Exception):
    pass


async def start_world(session: AsyncSession, world_id: int) -> World:
    result = await session.execute(select(World).where(World.id == world_id))
    world = result.scalar_one_or_none()
    if world is None:
        raise SeasonError("دنیا پیدا نشد.")
    if world.status != WorldStatus.UPCOMING:
        raise SeasonError("این دنیا از قبل شروع شده یا تموم شده.")

    now = dt.datetime.now(dt.timezone.utc)
    world.status = WorldStatus.ACTIVE
    world.started_at = now
    world.ends_at = now + dt.timedelta(days=world.season_length_days)
    return world


async def end_world(session: AsyncSession, world_id: int) -> World:
    result = await session.execute(select(World).where(World.id == world_id))
    world = result.scalar_one_or_none()
    if world is None:
        raise SeasonError("دنیا پیدا نشد.")
    await achievements.award_season_champion(session, world_id)
    world.status = WorldStatus.ENDED
    return world


async def advance_expired_worlds(session: AsyncSession) -> list[World]:
    """
    فراخوانی دوره‌ای (مثلاً هر ساعت) توسط scheduler: هر دنیایی که
    فعاله و زمانش تموم شده رو خودکار می‌بنده. لیست دنیاهای بسته‌شده
    رو برمی‌گردونه تا caller بتونه اعلان/آرشیو انجام بده.
    """
    now = dt.datetime.now(dt.timezone.utc)
    result = await session.execute(
        select(World).where(World.status == WorldStatus.ACTIVE, World.ends_at <= now)
    )
    expired = result.scalars().all()
    for world in expired:
        await achievements.award_season_champion(session, world.id)
        world.status = WorldStatus.ENDED
    return list(expired)


async def get_or_create_active_world(session: AsyncSession, *, name: str = "World 1") -> World:
    """
    برای شروع پروژه (وقتی هنوز پنل انتخاب چند-دنیا نداریم)، یک دنیای
    فعال پیش‌فرض برمی‌گردونه؛ اگه هیچ‌کدوم نبود می‌سازتش.
    """
    result = await session.execute(
        select(World).where(World.status == WorldStatus.ACTIVE).order_by(World.id)
    )
    world = result.scalars().first()
    if world is not None:
        return world

    world = World(name=name, status=WorldStatus.UPCOMING)
    session.add(world)
    await session.flush()
    return await start_world(session, world.id)


async def list_active_worlds(session: AsyncSession) -> list[World]:
    result = await session.execute(
        select(World).where(World.status == WorldStatus.ACTIVE).order_by(World.id)
    )
    return list(result.scalars().all())


async def create_world(
    session: AsyncSession, *, name: str, season_length_days: int = 45
) -> World:
    existing = await session.execute(select(World).where(World.name == name))
    if existing.scalar_one_or_none() is not None:
        raise SeasonError("دنیایی با این اسم از قبل هست.")
    world = World(name=name, status=WorldStatus.UPCOMING, season_length_days=season_length_days)
    session.add(world)
    await session.flush()
    return await start_world(session, world.id)

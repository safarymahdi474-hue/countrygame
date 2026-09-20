"""
زمان‌بند پروژه: هر `tick_interval_seconds` (طبق تنظیمات)، تولید همه‌ی
کشورهای همه‌ی دنیاهای فعال رو حساب می‌کنه، و هر ساعت هم دنیاهای
منقضی‌شده رو می‌بنده. از APScheduler استفاده می‌کنیم چون سبک‌تر از
راه‌اندازی یه صف/worker جداست و برای این مقیاس کافیه.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from bot.database.engine import session_scope
from bot.models.country import Country
from bot.models.world import World, WorldStatus
from bot.services.production_tick import run_production_tick
from bot.services.season import advance_expired_worlds
from bot.services.occupation import liberate_expired_occupations
from bot.services.upkeep import run_upkeep_tick
from bot.services.world_events import EVENT_EFFECTS, get_active_event, roll_new_event

logger = logging.getLogger(__name__)


async def _production_job(session_factory: async_sessionmaker, elapsed_seconds: int) -> None:
    async with session_scope(session_factory) as session:
        result = await session.execute(
            select(Country.id)
            .join(World, World.id == Country.world_id)
            .where(World.status == WorldStatus.ACTIVE)
        )
        country_ids = [row[0] for row in result.all()]
        for country_id in country_ids:
            try:
                await run_production_tick(session, country_id, elapsed_seconds=elapsed_seconds)
                await run_upkeep_tick(session, country_id, elapsed_seconds=elapsed_seconds)
            except Exception:
                logger.exception("خطا در تیک تولید/نگهداری برای کشور %s", country_id)
        logger.info("تیک تولید اجرا شد — %d کشور", len(country_ids))


async def _season_advance_job(session_factory: async_sessionmaker) -> None:
    async with session_scope(session_factory) as session:
        expired = await advance_expired_worlds(session)
        if expired:
            logger.info("دنیاهای منقضی‌شده بسته شدن: %s", [w.name for w in expired])
        liberated = await liberate_expired_occupations(session)
        if liberated:
            logger.info("کشورهای آزادشده: %s", [c.display_name for c in liberated])


async def _world_events_job(session_factory: async_sessionmaker) -> None:
    """برای هر دنیای فعال، اگه رویدادی فعال نیست یا تموم شده، یه رویداد تصادفی جدید می‌غلتونه."""
    async with session_scope(session_factory) as session:
        result = await session.execute(select(World.id, World.name).where(World.status == WorldStatus.ACTIVE))
        for world_id, world_name in result.all():
            active = await get_active_event(session, world_id)
            if active is not None:
                continue
            event = await roll_new_event(session, world_id)
            logger.info(
                "رویداد جدید تو %s: %s", world_name, EVENT_EFFECTS[event.event_type].description
            )


def build_scheduler(
    session_factory: async_sessionmaker, *, tick_interval_seconds: int
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        _production_job,
        trigger=IntervalTrigger(seconds=tick_interval_seconds),
        args=[session_factory, tick_interval_seconds],
        id="production_tick",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _season_advance_job,
        trigger=IntervalTrigger(minutes=30),
        args=[session_factory],
        id="season_advance",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _world_events_job,
        trigger=IntervalTrigger(hours=1),
        args=[session_factory],
        id="world_events",
        max_instances=1,
        coalesce=True,
    )

    return scheduler

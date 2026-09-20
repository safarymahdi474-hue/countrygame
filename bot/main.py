from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config.logging_config import configure_logging, init_sentry
from bot.config.settings import load_settings
from bot.database.engine import Base, build_engine, build_session_factory
from bot.handlers import (
    admin,
    borders,
    buildings,
    combat,
    diplomacy,
    errors,
    market,
    military,
    ranking,
    scout,
    start,
    status,
)
from bot.middlewares.db_session import DbSessionMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.services.scheduler import build_scheduler


async def main() -> None:
    settings = load_settings()
    configure_logging(debug=settings.debug)
    init_sentry(settings.sentry_dsn)

    engine = build_engine(settings.database_url, echo=settings.debug)
    async with engine.begin() as conn:
        # فقط برای توسعه‌ی محلی؛ رو دیتابیس واقعی از Alembic استفاده می‌کنیم
        await conn.run_sync(Base.metadata.create_all)

    session_factory = build_session_factory(engine)

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(ThrottlingMiddleware())
    dp.update.middleware(DbSessionMiddleware(session_factory))

    # دستورات ادمین فقط برای ADMIN_IDS تعریف‌شده تو تنظیمات فعالن
    admin.router.message.filter(F.from_user.id.in_(settings.admin_ids))

    dp.include_router(errors.router)
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(status.router)
    dp.include_router(buildings.router)
    dp.include_router(military.router)
    dp.include_router(combat.router)
    dp.include_router(scout.router)
    dp.include_router(ranking.router)
    dp.include_router(diplomacy.router)
    dp.include_router(market.router)
    dp.include_router(borders.router)

    scheduler = build_scheduler(session_factory, tick_interval_seconds=settings.tick_interval_seconds)
    scheduler.start()

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
